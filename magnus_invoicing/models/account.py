# -*- coding: utf-8 -*-
# Copyright 2018 Magnus ((www.magnus.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    _description = 'Analytic Line'
    _order = 'date desc'

    @api.multi
    @api.depends('date','product_uom_id')
    def _compute_week_month(self):
        for line in self:
            if line.product_uom_id != self.env.ref('product.'
                                                       'product_uom_hour'):
                continue
            if line.date:
                line.week_id = line.find_daterange_week(line.date)
                line.month_id = line.find_daterange_month(line.date)
            elif not line.child_ids == []:
                line.week_id = line.find_daterange_week(line.child_ids.date)
                line.month_id = line.find_daterange_month(line.child_ids.date)

    def find_daterange_week(self, date):
        """
        try to find a date range with type 'week'
        with @param:date contained in its date_start/date_end interval
        """
#        date_str = fields.Date.to_string(date)
        s_args = [
            ('type_name', '=', 'Week'),
            ('date_start', '<=', date),
            ('date_end', '>=', date),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False),
        ]
        date_range = self.env['date.range'].search(s_args,
                                                   limit=1,
                                                   order='company_id asc')
        return date_range

    def find_daterange_month(self, date):
        """
        try to find a date range with type 'month'
        with @param:date contained in its date_start/date_end interval
        """
#        date_str = fields.Date.to_string(date)
        s_args = [
            ('type_name', '=', 'Fiscal month'),
            ('date_start', '<=', date),
            ('date_end', '>=', date),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False),
        ]
        date_range = self.env['date.range'].search(
            s_args,
            limit=1,
            order='company_id asc'
        )
        return date_range

    @api.depends('task_id')
    def _onchange_project_task(self):
        for line in self:
            task = line.task_id
            if task:
                line.correction_charge = task.correction_charge
                line.chargeable = task.chargeable
                line.expenses = task.invoice_properties.expenses if task.invoice_properties else False

    invoiced = fields.Boolean(
        'Invoiced'
    )
    invoiceable = fields.Boolean(
        'Invoiceable'
    )
    # user_total_id = fields.Many2one(
    #     'analytic.user.total',
    #     string='Summary Reference',
    #     ondelete='cascade',
    #     index=True
    # )
    user_total_id = fields.Many2one(
        'analytic.user.total',
        string='Summary Reference',
        index=True
    )
    week_id = fields.Many2one(
        'date.range',
        compute=_compute_week_month,
        string='Week',
        store=True,
    )
    month_id = fields.Many2one(
        'date.range',
        compute=_compute_week_month,
        string='Month',
        store=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Confirmed'),
        ('delayed', 'Delayed'),
        ('invoiceable', 'To be Invoiced'),
        ('invoiced', 'Invoiced'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    correction_charge = fields.Boolean(
        compute=_onchange_project_task,
        string='Correction Chargeability',
        store=True,
    )
    chargeable = fields.Boolean(
        compute=_onchange_project_task,
        string='Chargeable',
        store=True,
    )
    expenses = fields.Boolean(
        compute=_onchange_project_task,
        string='Expenses',
        store=True,
    )


    def _check_state(self):
        """
        to check if any lines computes method calls allow to modify
        :return: True or super
        """
        context = self.env.context.copy()
        if not 'active_model' in context:
            return True
        return super(AccountAnalyticLine, self)._check_state()

    def get_task_user_product(self, task_id, user_id):
        taskUserObj = self.env['task.user']
        product_id = False
        if task_id and user_id:
            taskUser = taskUserObj.search([('task_id', '=', task_id), ('user_id', '=', user_id)],
                                          limit=1)
            product_id = taskUser.product_id.id if taskUser and taskUser.product_id else False
        return product_id

    @api.model
    def create(self, vals):
        if 'task_id' in vals and 'user_id' in vals:
            vals['product_id'] = self.get_task_user_product(vals['task_id'],vals['user_id'])
        return super(AccountAnalyticLine, self).create(vals)

    @api.multi
    def write(self, vals):
        for aal in self:
            task_id = vals['task_id'] if 'task_id' in vals else aal.task_id.id
            user_id = vals['user_id'] if 'user_id' in vals else aal.user_id.id
            if task_id and user_id:
                vals['product_id'] = self.get_task_user_product(task_id, user_id)
        return super(AccountAnalyticLine, self).write(vals)


    '''@api.model
    def create(self, vals):
#        import pdb; pdb.set_trace()
        res = super(AccountAnalyticLine, self).create(vals)
        if self._context.get('aal_loop', False):
            return res
        if res.product_uom_id == self.env.ref('product.product_uom_hour'):
            s_args1 = [
                ('week_id', '=', res.week_id.id),
                ('product_id', '=', res.product_id.id),
                ('user_id', '=', res.user_id.id),
                ('company_id', '=', res.company_id.id),
                ('task_id', '=', res.task_id.id),
                ('account_id', '=', res.account_id.id),
                ('partner_id', '=', res.partner_id.id),
                ('product_uom_id', '=', res.product_uom_id.id),
                ('child_ids', '!=', False),
            ]
            second1= self.search(s_args1)
            if len(second1) == 1:
                res.parent_id = second1.id
                second1.unit_amount += res.unit_amount
                second1.amount += res.amount
            s_args2 = [
                ('week_id', '=', res.week_id.id),
                ('product_id', '=', res.product_id.id),
                ('user_id', '=', res.user_id.id),
                ('company_id', '=', res.company_id.id),
                ('task_id', '=', res.task_id.id),
                ('account_id', '=', res.account_id.id),
                ('partner_id', '=', res.partner_id.id),
                ('product_uom_id', '=', res.product_uom_id.id),
                ('child_ids', '=', False),
            ]
            second2 = self.search(s_args2)
            if len(second2) > 1:
                values = {
                    'name': '/',
                    'week_id': res.week_id.id,
                    'product_id': res.product_id.id,
                    'user_id': res.user_id.id,
                    'company_id': res.company_id.id,
                    'task_id': res.task_id.id,
                    'account_id': res.account_id.id,
                    'partner_id': res.partner_id.id,
                    'product_uom_id': res.product_uom_id.id,
                }
                res2 = self.with_context(aal_loop=True).create(values)
                ua = 0
                a = 0
                for line in second2:
                    ua += line.unit_amount
                    a += line.amount
                    line.parent_id = res2.id
                res2.unit_amount = ua
                res2.amount = a
        return res'''

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    analytic_invoice_id = fields.Many2one(
        'analytic.invoice',
        string='Invoice Reference',
        ondelete='cascade',
        index=True
    )
    # project_id = fields.Many2one(
    #     'project.project',
    #     string='Project',
    #     index=True
    # )

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def _get_timesheet_by_group(self):
        self.ensure_one()
        aal_ids = []
        analytic_invoice_ids = self.invoice_line_ids.mapped('analytic_invoice_id')
        for analytic_invoice in analytic_invoice_ids:
            for grp_line in analytic_invoice.user_total_ids:
                aal_ids += grp_line.children_ids
        userProject = {}
        for aal in aal_ids:
            project_id, user_id = aal.project_id if aal.project_id else aal.task_id.project_id , aal.user_id
            if project_id.correction_charge and project_id.specs_invoice_report:
                if (project_id, user_id) in userProject:
                    userProject[(project_id, user_id)] = userProject[(project_id, user_id)] + [aal]
                else:
                    userProject[(project_id, user_id)] = [aal]
        return userProject

        


