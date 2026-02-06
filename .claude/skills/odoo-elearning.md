# Skill: Manage E-Learning Courses

Create and manage e-learning courses, lessons, and quizzes through the elearning_custom module.

## Usage
`/odoo-elearning <action> [options]`

Actions:
- `create-course` - Create a new course
- `add-section` - Add section to a course
- `add-lesson` - Add article/video/document lesson
- `add-quiz` - Add quiz with questions
- `build-full` - Build complete course structure
- `from-template` - Create from template
- `stats` - View course statistics

## Instructions

### Architecture Overview
The e-learning customization is in `/home/user/odoo/custom-addons/elearning_custom/`:
- `models/slide_channel.py` - Extends courses with difficulty, audience, quick-build
- `models/course_template.py` - Reusable course templates

MCP endpoints are in:
- `/home/user/odoo/custom-addons/odoo_mcp_server/controllers/mcp_elearning_controller.py`

### Key Models

**slide.channel (Course, extended):**
- `difficulty` - beginner/intermediate/advanced/expert
- `target_audience` - Who it's for
- `estimated_duration` - Expected hours
- `learning_objectives` - HTML objectives
- `certificate_enabled` - Issue certificates
- `source_channel` - manual/template/ai_mcp/import
- `quick_build_course()` - Build from structured data

**slide.slide (Lesson):**
- `slide_category` - article/video/document/infographic/quiz
- `html_content` - For articles
- `url` - For videos (YouTube, Vimeo, Google Drive)
- `is_category` - True for sections, False for content
- `question_ids` - Quiz questions (if quiz)

**elearning.course.template:**
- Predefined course structures
- 3 built-in templates: Onboarding, Product Training, Compliance
- `create_course_from_template()` - Instantiate a course

### Building a Complete Course via MCP

```json
POST /mcp/elearning/build-course
{
    "name": "Sales Mastery Program",
    "channel_type": "training",
    "visibility": "connected",
    "sections": [
        {
            "name": "Introduction",
            "slides": [
                {
                    "name": "Welcome",
                    "slide_category": "article",
                    "html_content": "<h2>Welcome!</h2><p>This course will...</p>",
                    "is_preview": true
                },
                {
                    "name": "Product Demo",
                    "slide_category": "video",
                    "url": "https://www.youtube.com/watch?v=..."
                }
            ]
        },
        {
            "name": "Assessment",
            "slides": [
                {
                    "name": "Final Quiz",
                    "slide_category": "quiz",
                    "questions": [
                        {
                            "question": "What is our main product?",
                            "answers": [
                                {"text": "ERP Software", "is_correct": true},
                                {"text": "Social Media", "is_correct": false},
                                {"text": "Cloud Storage", "is_correct": false}
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}
```

### Content Types
| Type | slide_category | Content Field | Notes |
|------|---------------|---------------|-------|
| Article | `article` | `html_content` | HTML with rich text |
| Video | `video` | `url` | YouTube, Vimeo, Google Drive |
| Document | `document` | `binary_content` or `url` | PDF, Office, Google Docs |
| Image | `infographic` | `binary_content` or `url` | PNG, JPG, etc. |
| Quiz | `quiz` | `question_ids` | Questions with answers |

### Templates Available
1. **Employee Onboarding** - 3 sections, beginner, ~4h
2. **Product Training** - 3 sections, intermediate, ~6h
3. **Compliance Training** - 2 sections, beginner, ~2h
