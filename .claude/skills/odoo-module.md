# Skill: Create Odoo Module

Create a new custom Odoo module in the `custom-addons/` directory.

## Usage
`/odoo-module <module_name> [--depends dep1,dep2] [--category Category]`

## Instructions

When the user asks to create a new Odoo module:

1. **Create the module directory** in `/home/user/odoo/custom-addons/<module_name>/`

2. **Generate the standard structure:**
   ```
   <module_name>/
   ├── __manifest__.py
   ├── __init__.py
   ├── models/
   │   └── __init__.py
   ├── views/
   ├── security/
   │   └── ir.model.access.csv
   ├── data/
   ├── controllers/
   │   └── __init__.py
   ├── wizards/
   │   └── __init__.py
   └── static/
       └── description/
   ```

3. **Generate `__manifest__.py`** with:
   - `name`: Human-readable name
   - `version`: `19.0.1.0.0`
   - `depends`: Always include `base`, add user-specified deps
   - `category`: From argument or ask
   - `license`: `LGPL-3`
   - `data`: Pre-populate with security CSV
   - `installable`: True

4. **Generate `ir.model.access.csv`** with a header row

5. **Follow Odoo conventions:**
   - Model names: `module.name` (dots)
   - Python class: `ModuleName` (CamelCase)
   - XML IDs: `module_name_view_type` (underscores)
   - Use `_inherit` to extend existing models
   - Use `_name` for new models

6. After creation, tell the user how to install:
   ```
   ./odoo-bin -u <module_name> --addons-path=addons,custom-addons
   ```
