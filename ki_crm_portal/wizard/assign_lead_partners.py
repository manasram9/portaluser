# -*- coding: utf-8 -*-


from odoo import api, fields, models, _

class Assign_partner(models.TransientModel):
    _name="crm.assign.partner"
    _description = "Assign CRM Partners"

    @api.model
    def default_get(self, fields):
        defaults = super(Assign_partner, self).default_get(fields)
        defaults['lead_id'] = self.env.context.get('active_id')
        return defaults

    lead_id = fields.Many2one(
        'crm.lead',
        required=True,
        readonly=True
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string="Partners",
        required=True
    )

    def action_assign(self):
        self.lead_id.assign_new_partner(self.partner_ids)