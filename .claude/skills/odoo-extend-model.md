# Skill: Extend Odoo Model

Extend an existing Odoo model by adding fields, methods, or overrides in a custom module.

## Usage
`/odoo-extend-model <model_name> [--module custom_module] [--fields field1:type,field2:type]`

## Instructions

When the user asks to extend/modify an Odoo model:

1. **First, analyze the existing model:**
   - Read the model's Python source in `addons/` to understand current fields and methods
   - Check for existing customizations in `custom-addons/`
   - Identify the model's `_name`, `_inherit`, `_description`

2. **Create or update the custom module:**
   - If no custom module specified, use an appropriate one in `custom-addons/`
   - NEVER modify files in `addons/` (the Odoo core)

3. **Add the model extension:**
   ```python
   from odoo import models, fields, api

   class ModelExtension(models.Model):
       _inherit = 'original.model.name'

       new_field = fields.Char('New Field')

       @api.depends('field')
       def _compute_something(self):
           ...
   ```

4. **Add views using `xpath`:**
   ```xml
   <record id="view_inherit" model="ir.ui.view">
       <field name="inherit_id" ref="original_module.original_view_id"/>
       <field name="arch" type="xml">
           <xpath expr="//field[@name='existing_field']" position="after">
               <field name="new_field"/>
           </xpath>
       </field>
   </record>
   ```

5. **Update security** in `ir.model.access.csv` if adding new models

6. **Key patterns:**
   - `_inherit = 'model.name'` to extend (same table)
   - `_name = 'new.model'` + `_inherit = 'model.name'` to create delegation
   - Override methods with `super()` calls
   - Use `@api.constrains` for validation
   - Use `@api.onchange` for UI reactivity
