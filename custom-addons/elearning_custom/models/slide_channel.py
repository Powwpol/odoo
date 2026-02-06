"""
Custom E-Learning Channel extensions.

Adds:
- Difficulty level
- Target audience
- Estimated total duration
- Certificate configuration
- Quick-build helper for MCP
"""
from odoo import models, fields, api


class SlideChannelCustom(models.Model):
    _inherit = 'slide.channel'

    # ----------------------------------------------------------------
    # New Fields
    # ----------------------------------------------------------------

    difficulty = fields.Selection([
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ], string='Difficulty Level', default='beginner')

    target_audience = fields.Char(
        'Target Audience',
        help='Who is this course for? (e.g. "New employees", "Sales managers")',
    )

    estimated_duration = fields.Float(
        'Estimated Duration (hours)',
        help='Expected time to complete the course.',
    )

    learning_objectives = fields.Html(
        'Learning Objectives',
        help='What will participants learn?',
    )

    certificate_enabled = fields.Boolean(
        'Certificate of Completion',
        help='Issue a certificate when the course is completed.',
    )

    course_template_id = fields.Many2one(
        'elearning.course.template',
        string='Created from Template',
        help='Template used to create this course.',
    )

    source_channel = fields.Selection([
        ('manual', 'Manual'),
        ('template', 'From Template'),
        ('ai_mcp', 'AI / MCP'),
        ('import', 'Imported'),
    ], string='Creation Source', default='manual')

    # ----------------------------------------------------------------
    # Quick-Build for MCP
    # ----------------------------------------------------------------

    @api.model
    def quick_build_course(self, name, sections_data, **kwargs):
        """Build a complete course from structured data (for MCP/AI).

        Args:
            name: Course title
            sections_data: List of sections:
                [
                    {
                        "name": "Introduction",
                        "slides": [
                            {"name": "Welcome", "type": "article", "content": "<p>...</p>"},
                            {"name": "Overview Video", "type": "video", "url": "https://..."},
                            {"name": "Quiz 1", "type": "quiz", "questions": [...]}
                        ]
                    }
                ]
            **kwargs: difficulty, target_audience, estimated_duration,
                      description, visibility, etc.

        Returns:
            dict with course info
        """
        course_vals = {
            'name': name,
            'source_channel': 'ai_mcp',
        }

        for field in ['difficulty', 'target_audience', 'estimated_duration',
                       'description', 'description_short', 'channel_type',
                       'visibility', 'enroll', 'website_published',
                       'learning_objectives', 'certificate_enabled']:
            if field in kwargs:
                course_vals[field] = kwargs[field]

        if kwargs.get('tag_ids'):
            course_vals['tag_ids'] = [(6, 0, kwargs['tag_ids'])]

        channel = self.create(course_vals)
        slides_created = []
        seq = 0

        for section in sections_data:
            seq += 1
            self.env['slide.slide'].create({
                'channel_id': channel.id,
                'name': section['name'],
                'is_category': True,
                'sequence': seq * 10,
            })

            for slide_data in section.get('slides', []):
                seq += 1
                slide_vals = {
                    'channel_id': channel.id,
                    'name': slide_data['name'],
                    'sequence': seq * 10,
                }

                stype = slide_data.get('type', 'article')
                slide_vals['slide_category'] = stype

                if stype == 'article':
                    slide_vals['html_content'] = slide_data.get('content', '')
                elif stype == 'video':
                    slide_vals['url'] = slide_data.get('url', '')
                elif stype == 'quiz' and slide_data.get('questions'):
                    q_cmds = []
                    for qi, q in enumerate(slide_data['questions']):
                        a_cmds = [(0, 0, {
                            'sequence': ai,
                            'text_value': a['text'],
                            'is_correct': a.get('is_correct', False),
                            'comment': a.get('comment', ''),
                        }) for ai, a in enumerate(q.get('answers', []))]
                        q_cmds.append((0, 0, {
                            'sequence': qi,
                            'question': q['question'],
                            'answer_ids': a_cmds,
                        }))
                    slide_vals['question_ids'] = q_cmds

                if slide_data.get('is_preview'):
                    slide_vals['is_preview'] = True
                if slide_data.get('completion_time'):
                    slide_vals['completion_time'] = slide_data['completion_time']

                slide = self.env['slide.slide'].create(slide_vals)
                slides_created.append({'id': slide.id, 'name': slide.name, 'type': stype})

        return {
            'id': channel.id,
            'name': channel.name,
            'total_slides': channel.total_slides,
            'slides': slides_created,
        }
