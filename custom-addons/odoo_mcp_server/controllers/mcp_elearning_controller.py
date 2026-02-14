"""
MCP Controller - E-Learning endpoints.

Provides course creation, slide/lesson management, quiz creation,
and enrollment tracking through the MCP protocol.
"""
import json
import logging

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError, ValidationError, UserError

_logger = logging.getLogger(__name__)


class MCPElearningController(http.Controller):
    """E-Learning endpoints for the MCP server."""

    # ----------------------------------------------------------------
    # Course Management
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/elearning/create-course',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_course(self, name, **kwargs):
        """Create a new e-learning course.

        Args:
            name: Course title
            **kwargs:
                - description: Course description (HTML)
                - description_short: Short description for cards
                - channel_type: 'training' or 'documentation' (default 'training')
                - visibility: 'public', 'connected', 'members', 'link'
                - enroll: 'public' or 'invite'
                - tag_ids: List of tag IDs
                - website_published: Publish immediately (default False)
                - allow_comment: Allow comments (default True)
        """
        try:
            vals = {'name': name}

            for field in ['description', 'description_short', 'channel_type',
                          'visibility', 'enroll', 'website_published', 'allow_comment']:
                if field in kwargs:
                    vals[field] = kwargs[field]

            if kwargs.get('tag_ids'):
                vals['tag_ids'] = [(6, 0, kwargs['tag_ids'])]

            channel = request.env['slide.channel'].create(vals)

            return {
                'id': channel.id,
                'name': channel.name,
                'channel_type': channel.channel_type,
                'visibility': channel.visibility,
                'enroll': channel.enroll,
                'website_published': channel.website_published,
                'access_token': channel.access_token,
            }

        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}
        except Exception as e:
            _logger.exception("MCP elearning/create-course error")
            return {'error': str(e)}

    @http.route(
        '/mcp/elearning/create-section',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_section(self, channel_id, name, sequence=0):
        """Create a section/category within a course.

        Args:
            channel_id: Course ID
            name: Section title
            sequence: Display order
        """
        try:
            section = request.env['slide.slide'].create({
                'channel_id': channel_id,
                'name': name,
                'is_category': True,
                'sequence': sequence,
            })

            return {
                'id': section.id,
                'name': section.name,
                'sequence': section.sequence,
                'is_category': True,
            }

        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}

    # ----------------------------------------------------------------
    # Slide / Lesson Management
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/elearning/create-slide',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_slide(self, channel_id, name, slide_category, **kwargs):
        """Create a new slide/lesson in a course.

        Args:
            channel_id: Course ID
            name: Slide title
            slide_category: Content type - 'article', 'video', 'document',
                            'infographic', 'quiz'
            **kwargs:
                - html_content: HTML content (for articles)
                - url: External URL (video URL for YouTube/Vimeo, Google Drive)
                - description: Slide description
                - sequence: Display order
                - is_preview: Allow preview without enrollment
                - is_published: Publish immediately
                - tag_ids: Tag IDs list
                - completion_time: Duration in hours
        """
        try:
            vals = {
                'channel_id': channel_id,
                'name': name,
                'slide_category': slide_category,
            }

            for field in ['html_content', 'url', 'description', 'sequence',
                          'is_preview', 'is_published', 'completion_time']:
                if field in kwargs:
                    vals[field] = kwargs[field]

            if kwargs.get('tag_ids'):
                vals['tag_ids'] = [(6, 0, kwargs['tag_ids'])]

            slide = request.env['slide.slide'].create(vals)

            return {
                'id': slide.id,
                'name': slide.name,
                'slide_category': slide.slide_category,
                'slide_type': slide.slide_type,
                'sequence': slide.sequence,
                'is_published': slide.is_published,
                'completion_time': slide.completion_time,
            }

        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}
        except Exception as e:
            _logger.exception("MCP elearning/create-slide error")
            return {'error': str(e)}

    @http.route(
        '/mcp/elearning/create-article',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_article(self, channel_id, name, html_content, **kwargs):
        """Shortcut to create an article slide with HTML content.

        Args:
            channel_id: Course ID
            name: Article title
            html_content: Full HTML content
            **kwargs: Same optional fields as create-slide
        """
        kwargs['html_content'] = html_content
        kwargs['slide_category'] = 'article'
        return self.create_slide(channel_id, name, 'article', **kwargs)

    @http.route(
        '/mcp/elearning/create-video',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_video(self, channel_id, name, url, **kwargs):
        """Shortcut to create a video slide.

        Args:
            channel_id: Course ID
            name: Video title
            url: YouTube, Vimeo, or Google Drive URL
            **kwargs: Same optional fields as create-slide
        """
        kwargs['url'] = url
        return self.create_slide(channel_id, name, 'video', **kwargs)

    # ----------------------------------------------------------------
    # Quiz Management
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/elearning/create-quiz',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_quiz(self, channel_id, name, questions, **kwargs):
        """Create a quiz slide with questions and answers.

        Args:
            channel_id: Course ID
            name: Quiz title
            questions: List of questions, each with:
                - question: Question text
                - answers: List of answers, each with:
                    - text: Answer text
                    - is_correct: Boolean
                    - comment: Feedback text (optional)
            **kwargs:
                - sequence: Display order
                - is_published: Publish immediately
                - quiz_first_attempt_reward: Karma for 1st attempt (default 10)
                - quiz_second_attempt_reward: Karma for 2nd attempt (default 7)
                - quiz_third_attempt_reward: Karma for 3rd attempt (default 5)
        """
        try:
            # Build question commands
            question_cmds = []
            for q_idx, q in enumerate(questions):
                answer_cmds = []
                for a_idx, a in enumerate(q.get('answers', [])):
                    answer_cmds.append((0, 0, {
                        'sequence': a_idx,
                        'text_value': a['text'],
                        'is_correct': a.get('is_correct', False),
                        'comment': a.get('comment', ''),
                    }))

                question_cmds.append((0, 0, {
                    'sequence': q_idx,
                    'question': q['question'],
                    'answer_ids': answer_cmds,
                }))

            vals = {
                'channel_id': channel_id,
                'name': name,
                'slide_category': 'quiz',
                'question_ids': question_cmds,
            }

            for field in ['sequence', 'is_published', 'quiz_first_attempt_reward',
                          'quiz_second_attempt_reward', 'quiz_third_attempt_reward']:
                if field in kwargs:
                    vals[field] = kwargs[field]

            slide = request.env['slide.slide'].create(vals)

            return {
                'id': slide.id,
                'name': slide.name,
                'slide_category': 'quiz',
                'questions_count': slide.questions_count,
                'is_published': slide.is_published,
            }

        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}
        except Exception as e:
            _logger.exception("MCP elearning/create-quiz error")
            return {'error': str(e)}

    # ----------------------------------------------------------------
    # Course Operations & Enrollment
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/elearning/enroll',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def enroll_members(self, channel_id, partner_ids):
        """Enroll partners (users) in a course.

        Args:
            channel_id: Course ID
            partner_ids: List of partner IDs to enroll
        """
        try:
            channel = request.env['slide.channel'].browse(channel_id)
            if not channel.exists():
                return {'error': f'Course {channel_id} not found'}

            partners = request.env['res.partner'].browse(partner_ids)
            channel._action_add_members(partners)

            return {
                'success': True,
                'course': channel.name,
                'enrolled_count': len(partner_ids),
                'total_members': channel.members_count,
            }

        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}

    @http.route(
        '/mcp/elearning/course-stats',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def course_stats(self, channel_id=None):
        """Get course statistics and progress.

        Args:
            channel_id: Specific course ID (optional, returns all if omitted)
        """
        try:
            if channel_id:
                channels = request.env['slide.channel'].browse(channel_id)
            else:
                channels = request.env['slide.channel'].search([])

            results = []
            for ch in channels:
                results.append({
                    'id': ch.id,
                    'name': ch.name,
                    'channel_type': ch.channel_type,
                    'website_published': ch.website_published,
                    'total_slides': ch.total_slides,
                    'total_time': ch.total_time,
                    'total_views': ch.total_views,
                    'total_votes': ch.total_votes,
                    'rating_avg_stars': ch.rating_avg_stars,
                    'members_count': ch.members_count,
                    'members_completed': ch.members_completed_count,
                    'members_engaged': ch.members_engaged_count,
                    'content_breakdown': {
                        'articles': ch.nbr_article,
                        'videos': ch.nbr_video,
                        'documents': ch.nbr_document,
                        'infographics': ch.nbr_infographic,
                        'quizzes': ch.nbr_quiz,
                    },
                })

            return {'courses': results}

        except Exception as e:
            return {'error': str(e)}

    # ----------------------------------------------------------------
    # Build Full Course (Compound)
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/elearning/build-course',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def build_full_course(self, name, sections, **kwargs):
        """Build a complete course with sections, slides, and quizzes in one call.

        Args:
            name: Course title
            sections: List of sections, each with:
                - name: Section title
                - slides: List of slides, each with:
                    - name: Slide title
                    - slide_category: 'article', 'video', 'document', 'quiz'
                    - html_content: For articles
                    - url: For videos
                    - questions: For quizzes (list of question objects)
                    - is_preview: Allow preview
            **kwargs: Course-level settings (same as create-course)
        """
        try:
            # Create the course
            course_vals = {'name': name}
            for field in ['description', 'description_short', 'channel_type',
                          'visibility', 'enroll', 'website_published', 'allow_comment']:
                if field in kwargs:
                    course_vals[field] = kwargs[field]

            if kwargs.get('tag_ids'):
                course_vals['tag_ids'] = [(6, 0, kwargs['tag_ids'])]

            channel = request.env['slide.channel'].create(course_vals)

            slides_created = []
            global_seq = 0

            for sec_idx, section in enumerate(sections):
                # Create section
                global_seq += 1
                sec = request.env['slide.slide'].create({
                    'channel_id': channel.id,
                    'name': section['name'],
                    'is_category': True,
                    'sequence': global_seq * 10,
                })
                slides_created.append({
                    'id': sec.id,
                    'name': sec.name,
                    'type': 'section',
                })

                # Create slides within section
                for slide_data in section.get('slides', []):
                    global_seq += 1
                    slide_vals = {
                        'channel_id': channel.id,
                        'name': slide_data['name'],
                        'slide_category': slide_data.get('slide_category', 'article'),
                        'sequence': global_seq * 10,
                        'is_preview': slide_data.get('is_preview', False),
                    }

                    if slide_data.get('html_content'):
                        slide_vals['html_content'] = slide_data['html_content']
                    if slide_data.get('url'):
                        slide_vals['url'] = slide_data['url']
                    if slide_data.get('description'):
                        slide_vals['description'] = slide_data['description']
                    if slide_data.get('completion_time'):
                        slide_vals['completion_time'] = slide_data['completion_time']

                    # Handle quiz questions
                    if slide_data.get('slide_category') == 'quiz' and slide_data.get('questions'):
                        question_cmds = []
                        for q_idx, q in enumerate(slide_data['questions']):
                            answer_cmds = []
                            for a_idx, a in enumerate(q.get('answers', [])):
                                answer_cmds.append((0, 0, {
                                    'sequence': a_idx,
                                    'text_value': a['text'],
                                    'is_correct': a.get('is_correct', False),
                                    'comment': a.get('comment', ''),
                                }))
                            question_cmds.append((0, 0, {
                                'sequence': q_idx,
                                'question': q['question'],
                                'answer_ids': answer_cmds,
                            }))
                        slide_vals['question_ids'] = question_cmds

                    slide = request.env['slide.slide'].create(slide_vals)
                    slides_created.append({
                        'id': slide.id,
                        'name': slide.name,
                        'type': slide.slide_category,
                    })

            return {
                'course_id': channel.id,
                'course_name': channel.name,
                'total_slides': channel.total_slides,
                'slides_created': slides_created,
                'access_token': channel.access_token,
            }

        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}
        except Exception as e:
            _logger.exception("MCP elearning/build-course error")
            return {'error': str(e)}

    # ----------------------------------------------------------------
    # Tags & Discovery
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/elearning/tags',
        type='http',
        auth='bearer',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def list_tags(self, **kwargs):
        """List all available course tags and tag groups."""
        try:
            groups = request.env['slide.channel.tag.group'].search([])
            result = []
            for g in groups:
                result.append({
                    'group_id': g.id,
                    'group_name': g.name,
                    'tags': [
                        {'id': t.id, 'name': t.name, 'color': t.color}
                        for t in g.tag_ids
                    ],
                })
            return Response(
                json.dumps({'tag_groups': result}),
                content_type='application/json',
                status=200,
            )
        except Exception as e:
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500,
            )

    @http.route(
        '/mcp/elearning/courses',
        type='http',
        auth='bearer',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def list_courses(self, **kwargs):
        """List all courses with basic info."""
        try:
            keyword = kwargs.get('filter', '').lower()
            channels = request.env['slide.channel'].search([])
            result = []
            for ch in channels:
                if keyword and keyword not in (ch.name or '').lower():
                    continue
                result.append({
                    'id': ch.id,
                    'name': ch.name,
                    'channel_type': ch.channel_type,
                    'visibility': ch.visibility,
                    'website_published': ch.website_published,
                    'total_slides': ch.total_slides,
                    'members_count': ch.members_count,
                    'total_time': ch.total_time,
                })
            return Response(
                json.dumps({'courses': result}),
                content_type='application/json',
                status=200,
            )
        except Exception as e:
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500,
            )
