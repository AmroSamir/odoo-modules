# Technology Stack

**Analysis Date:** 2026-03-30

## Languages

**Primary:**
- Python 3.12 - All backend logic in `extra-addons/custom/creative_studio/models/` and `wizards/`
- XML - Odoo views and configuration in `views/` and `security/` directories
- JavaScript (OWL framework) - Frontend UI components in `static/src/js/`

**Secondary:**
- HTML - Template definitions in `static/src/xml/`
- CSS - Styling in `static/src/css/proofing.css`
- CSV - Security access control in `security/ir.model.access.csv`

## Runtime

**Environment:**
- Odoo 19 (Enterprise)
- Python 3.12
- PostgreSQL 17 (with pgvector extension for vector operations)

**Package Manager:**
- pip (Python package management via Odoo's built-in dependency system)
- Odoo's internal module loader

## Frameworks

**Core:**
- Odoo 19 Enterprise Framework - Complete ERP system providing ORM, authentication, views, and business logic foundation
- Mail module (`mail.thread`, `mail.activity.mixin`) - Email tracking, messaging, and activity management
- Portal module - User portal functionality for external access
- Base module - Core Odoo models including `res.users`, `res.groups`, `ir.attachment`

**Frontend:**
- OWL (Object Web Library) - Odoo's reactive component framework for JavaScript UIs
  - Used in `static/src/js/review_page.js` and `static/src/js/project_dashboard.js`
  - Registry system for custom actions and components

**Backend Architecture:**
- Odoo Model Layer (`models.Model`, `models.TransientModel`) - ORM for database abstraction
- Workflow/State Management - Selection fields for status tracking (not_started, in_review, approved, changes_requested)
- Actions System - Window actions and client actions for navigation

## Key Dependencies

**Critical:**
- Odoo 19 Base - Required as dependency in `__manifest__.py` (provides `res.users`, `res.groups`, security)
- Odoo 19 Mail - Required for tracking threads and activity mixins on `proofing.project`, `proofing.file`
- Odoo 19 Portal - Required for portal functionality (external user access)
- markupsafe - HTML escaping library used in `proofing_file.py` for safe HTML handling in annotations

**Infrastructure:**
- PostgreSQL 17 - Database backend with pgvector support (in Docker environment)
- Docker/Docker Compose - Deployment containerization on Contabo VPS

## Configuration

**Environment:**
- Runs within Odoo environment via Docker Compose
- Configuration via XML data files (not yet deployed to `data/` directory)
- Database name: lowercase required (Odoo 19 constraint)

**Build/Deployment:**
- Git-based deployment to Contabo VPS production and staging
- Docker containers: `web_odoo` (production, port 8069), `web_odoo_staging` (staging, port 8169)
- Module activation via Odoo UI: Apps → Update Apps List → Install module

## Platform Requirements

**Development:**
- Odoo 19 Enterprise license (required for enterprise activation via `odoo_unlimited` module)
- Python 3.12 development environment
- Text editor or IDE with Python/XML support

**Production:**
- Odoo 19 Enterprise running on Contabo VPS with Docker Compose
- PostgreSQL 17 database (pgvector enabled)
- Nginx reverse proxy with SSL
- Minimum 2GB RAM, storage for file attachments in `odoo-data/filestore/`

**Deployment Target:**
- Docker containers (web_odoo for production, web_odoo_staging for testing)
- SFTP/Git access to VPS for module deployment

---

*Stack analysis: 2026-03-30*
