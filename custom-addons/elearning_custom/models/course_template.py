"""
Course Templates for quick E-Learning creation.

Predefined course structures that can be instantiated
through MCP or the UI.
"""
from odoo import models, fields, api


class ElearningCourseTemplate(models.Model):
    _name = 'elearning.course.template'
    _description = 'E-Learning Course Template'
    _order = 'sequence, name'

    name = fields.Char('Template Name', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # Course defaults
    channel_type = fields.Selection([
        ('training', 'Training'),
        ('documentation', 'Documentation'),
    ], string='Course Type', default='training')
    difficulty = fields.Selection([
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ], string='Difficulty', default='beginner')
    target_audience = fields.Char('Target Audience')
    estimated_duration = fields.Float('Estimated Duration (hours)')
    description = fields.Html('Default Description')
    learning_objectives = fields.Html('Learning Objectives')

    # Template structure
    section_ids = fields.One2many(
        'elearning.course.template.section',
        'template_id',
        string='Sections',
    )

    # Stats
    usage_count = fields.Integer(
        'Times Used',
        compute='_compute_usage_count',
    )

    def _compute_usage_count(self):
        for tpl in self:
            tpl.usage_count = self.env['slide.channel'].search_count([
                ('course_template_id', '=', tpl.id),
            ])

    def create_course_from_template(self, name=None, **overrides):
        """Instantiate a course from this template.

        Args:
            name: Course name (defaults to template name)
            **overrides: Override any template default

        Returns:
            slide.channel record
        """
        self.ensure_one()
        vals = {
            'name': name or self.name,
            'channel_type': self.channel_type,
            'source_channel': 'template',
            'course_template_id': self.id,
            'difficulty': self.difficulty,
            'target_audience': self.target_audience,
            'estimated_duration': self.estimated_duration,
            'learning_objectives': self.learning_objectives,
        }
        if self.description:
            vals['description'] = self.description

        vals.update(overrides)
        channel = self.env['slide.channel'].create(vals)

        # Create sections and placeholder slides
        seq = 0
        for section in self.section_ids:
            seq += 1
            self.env['slide.slide'].create({
                'channel_id': channel.id,
                'name': section.name,
                'is_category': True,
                'sequence': seq * 10,
            })

            for slide_tpl in section.slide_ids:
                seq += 1
                slide_vals = {
                    'channel_id': channel.id,
                    'name': slide_tpl.name,
                    'slide_category': slide_tpl.slide_category,
                    'sequence': seq * 10,
                    'is_preview': slide_tpl.is_preview,
                }
                if slide_tpl.html_content:
                    slide_vals['html_content'] = slide_tpl.html_content
                if slide_tpl.completion_time:
                    slide_vals['completion_time'] = slide_tpl.completion_time

                self.env['slide.slide'].create(slide_vals)

        return channel


class ElearningCourseTemplateSection(models.Model):
    _name = 'elearning.course.template.section'
    _description = 'Course Template Section'
    _order = 'sequence'

    template_id = fields.Many2one(
        'elearning.course.template',
        string='Template',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char('Section Name', required=True, translate=True)
    sequence = fields.Integer(default=10)

    slide_ids = fields.One2many(
        'elearning.course.template.slide',
        'section_id',
        string='Slides',
    )


class ElearningCourseTemplateSlide(models.Model):
    _name = 'elearning.course.template.slide'
    _description = 'Course Template Slide'
    _order = 'sequence'

    section_id = fields.Many2one(
        'elearning.course.template.section',
        string='Section',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char('Slide Name', required=True, translate=True)
    sequence = fields.Integer(default=10)
    slide_category = fields.Selection([
        ('article', 'Article'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('infographic', 'Image'),
        ('quiz', 'Quiz'),
    ], string='Content Type', default='article', required=True)
    is_preview = fields.Boolean('Allow Preview')
    html_content = fields.Html('Default Content')
    completion_time = fields.Float('Duration (hours)')
