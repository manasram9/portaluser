from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import \
    CustomerPortal, pager as portal_pager, get_records_pager
from collections import OrderedDict
from operator import itemgetter
from odoo.tools import groupby as groupbyelem
from odoo.osv.expression import OR
import base64


class CRM_portal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CRM_portal, self)._prepare_portal_layout_values()
        values['crm_count'] = request.env['crm.lead'].search_count(
            [('type', '=', 'opportunity'), ('partner_id', '=', request.env.user.partner_id.id),
             ('is_master_opportunity', '=', False)])
        return values

    @http.route(['/my/crm', '/my/crm/page/<int:page>'], type='http', auth="user", website=True)
    def crm_portal_list_view(self, page=1, date_begin=None, date_end=None, sortby='bid_date_asc', filterby=None,
                             search=None,
                             search_in='bid', groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        crm_order = request.env['crm.lead']

        domain = [('type', '=', 'opportunity'), ('partner_id', '=', request.env.user.partner_id.id),
                  ('is_master_opportunity', '=', False)]

        searchbar_sortings = {
            'bid_date_asc': {'label': _('Close Date Asc'), 'order': 'bid_closing_date asc, id asc'},
            'bid_date': {'label': _('Close Date Desc'), 'order': 'bid_closing_date desc, id desc'},
            'date': {'label': _('Given Date Desc'), 'order': 'create_date desc, id desc'},
            'date_asc': {'label': _('Given Date Asc'), 'order': 'create_date asc, id asc'},
            'rev_asc': {'label': _('Revenue Highest'), 'order': 'planned_revenue desc, id desc'},
            'rev_desc': {'label': _('Revenue Lowest'), 'order': 'planned_revenue asc, id asc'},
            'qty_asc': {'label': _('Quantity Highest'), 'order': 'x_studio_quantity desc, id desc'},
            'qty_desc': {'label': _('Quantity Lowest'), 'order': 'x_studio_quantity asc, id asc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'paired_cat': {'label': _('Paired Catalog'), 'domain': [('is_paired_catelog', '=', True)]},
            'participated': {'label': _('Participated'), 'domain': [('is_participated', '=', True)]},
            'l1': {'label': _('L1'), 'domain': [('is_l1', '=', True)]},
            'cont_rved': {'label': _('Contract Received'), 'domain': [('is_contract_received', '=', True)]},
            'star3': {'label': _('3 Star'), 'domain': [('priority', '=', 3)]},
            'star2': {'label': _('2 Star'), 'domain': [('priority', '=', 2)]},
            'star1': {'label': _('1 Star'), 'domain': [('priority', '=', 1)]},
            'star0': {'label': _('No Star'), 'domain': [('priority', '=', 0)]}
        }
        searchbar_inputs = {
            'bid': {'input': 'bid', 'label': _('Search in #BID')},
            'stage': {'input': 'stage', 'label': _('Search in Stages')},
            'category': {'input': 'category', 'label': _('Search in Category')},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'stage': {'input': 'stage', 'label': _('Stage')},
            'date': {'input': 'date', 'label': _('Closing Date')},
            'date_week': {'input': 'date', 'label': _('Closing Week')},
            'date_month': {'input': 'date', 'label': _('Closing Month')},
            'date_quarter': {'input': 'date', 'label': _('Closing Quarter')},
            'date_year': {'input': 'date', 'label': _('Closing Year')},
            'create_date': {'input': 'date', 'label': _('Given Date')},
            'create_week': {'input': 'date', 'label': _('Given Week')},
            'create_month': {'input': 'date', 'label': _('Given Month')},
            'create_quarter': {'input': 'date', 'label': _('Given Quarter')},
            'create_year': {'input': 'date', 'label': _('Given Year')},
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        archive_groups = self._get_archive_groups('crm.lead', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('bid'):
                search_domain = OR(
                    [search_domain, [('name', 'ilike', search)]])
            if search_in in ('category'):
                search_domain = OR(
                    [search_domain, [('x_studio_product_category', 'ilike', search)]])
            if search_in in ('stage'):
                search_domain = OR([search_domain, [('stage_id', 'ilike', search)]])
            domain += search_domain

        crm_count = crm_order.search_count(domain)
        pager = portal_pager(
            url="/my/crm",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=crm_count,
            page=page,
            step=self._items_per_page
        )

        def call_search_method(domain=[]):
            return request.env['crm.lead'].search(domain, order=order, limit=self._items_per_page,
                                                  offset=(page - 1) * self._items_per_page)

        tasks = request.env['crm.lead'].search(domain, order=order, limit=self._items_per_page,
                                               offset=(page - 1) * self._items_per_page)

        lead_sudo = request.env['crm.lead'].sudo()
        if groupby == 'stage':
            grouped_tasks = [
                [request.env['crm.lead'].concat(*g)[0].stage_id.name if request.env['crm.lead'].concat(*g) else '',
                 request.env['crm.lead'].concat(*g)] for k, g in groupbyelem(tasks, itemgetter('stage_id'))]
        elif groupby == 'date':
            time_data = lead_sudo.read_group(domain, ['bid_closing_date'],
                                             ['bid_closing_date:day'])
            grouped_tasks = [[k['bid_closing_date:day'], call_search_method(k['__domain'])] for k in time_data]
        elif groupby == 'date_week':
            time_data = lead_sudo.read_group(domain, ['bid_closing_date'],
                                             ['bid_closing_date:week'])
            grouped_tasks = [[k['bid_closing_date:week'], call_search_method(k['__domain'])] for k in time_data]
        elif groupby == 'date_month':
            time_data = lead_sudo.read_group(domain, ['bid_closing_date'],
                                             ['bid_closing_date:month'])
            grouped_tasks = [[k['bid_closing_date:month'], call_search_method(k['__domain'])] for k in time_data]
        elif groupby == 'date_quarter':
            time_data = lead_sudo.read_group(domain, ['bid_closing_date'],
                                             ['bid_closing_date:quarter'])
            grouped_tasks = [[k['bid_closing_date:quarter'], call_search_method(k['__domain'])] for k in time_data]
        elif groupby == 'date_year':
            time_data = lead_sudo.read_group(domain, ['bid_closing_date'],
                                             ['bid_closing_date:year'])
            grouped_tasks = [[k['bid_closing_date:year'], call_search_method(k['__domain'])] for k in time_data]
        elif groupby == 'create_date':
            time_data = lead_sudo.read_group(domain, ['create_date'], ['create_date:day'])
            grouped_tasks = [[k['create_date:day'], call_search_method(k['__domain'])] for k in time_data]
        elif groupby == 'create_week':
            time_data = lead_sudo.read_group(domain, ['create_date'], ['create_date:week'])
            grouped_tasks = [[k['create_date:week'], call_search_method(k['__domain'])] for k in time_data]
        elif groupby == 'create_month':
            time_data = lead_sudo.read_group(domain, ['create_date'], ['create_date:month'])
            grouped_tasks = [[k['create_date:month'], call_search_method(k['__domain'])] for k in time_data]
        elif groupby == 'create_quarter':
            time_data = lead_sudo.read_group(domain, ['create_date'], ['create_date:quarter'])
            grouped_tasks = [[k['create_date:quarter'], call_search_method(k['__domain'])] for k in time_data]
        elif groupby == 'create_year':
            time_data = lead_sudo.read_group(domain, ['create_date'], ['create_date:year'])
            grouped_tasks = [[k['create_date:year'], call_search_method(k['__domain'])] for k in time_data]
        else:
            grouped_tasks = [['', tasks]]

        orders = crm_order.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session['my_assigned_bid_history'] = orders.ids[:100]
        values.update({
            'crm_leads': orders,
            'page_name': 'crm',
            'default_url': '/my/crm',
            'date': date_begin,
            'date_end': date_end,
            'grouped_tasks': grouped_tasks,
            'archive_groups': archive_groups,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'search': search,
            'reset_url': '/my/crm'
        })
        return request.render("ki_crm_portal.crm__portal_template_list", values)

    @http.route(['/my/crm/<int:crm_id>', '/my/crm/<int:crm_id>/<int:crm_no>'], type='http', auth="user", website=True)
    def crm_portal_form_view(self, crm_id, access_token=None, priority=False, **kw):
        try:
            order_sudo = self._document_check_access('crm.lead', crm_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if priority:
            order_sudo.priority = priority
            return request.redirect('/my/crm/' + str(order_sudo.id))

        values = {
            'crm_recs': order_sudo,
            'attachments': request.env['ir.attachment'].sudo().search(
                [('res_model', '=', order_sudo._name), ('res_id', '=', order_sudo.id)]) if order_sudo else [],
            'token': access_token,
            'report_type': 'html',
            'page_name': 'crm',
            'display_composer': True,
            'lost_selection': request.env['crm.lost.reason'].search([])
        }
        new_vals = self._get_page_view_values(order_sudo, access_token, values, 'my_assigned_bid_history', False, **kw)
        return request.render('ki_crm_portal.crm__portal_template_form', new_vals)

    @http.route(['/bid/button/<int:crm_bid_id>'], type='http', auth='user', website=True)
    def portal_Bid_button_click(self, crm_bid_id, participated=None, is_l1=None, contract_rcvd=None, lost=None,
                                paired_catelog=None, **kw):
        bid_id = request.env['crm.lead'].browse(crm_bid_id)
        url = '/'
        if bid_id:
            attact_sudo = request.env['ir.attachment'].sudo()
            if lost and kw.get('reason_id'):
                bid_id.write({'is_bid_lost': True, 'lost_reason': kw.get('reason_id')})
                bid_id.sudo().action_set_lost()
            elif participated:
                participated_attach = kw.get('participated_attach')
                if participated_attach:
                    attachment_value = {
                        'name': participated_attach.filename,
                        'datas': base64.encodestring(participated_attach.read()),
                        'datas_fname': participated_attach.filename,
                        'res_model': 'crm.lead',
                        'res_id': bid_id.id,
                    }
                    attact_sudo.create(attachment_value)
                bid_id.sudo().set_oppor_stage_participated()
            elif is_l1:
                bid_id.sudo().set_oppor_stage_l1()
            elif paired_catelog:
                paired_cat_Attach = kw.get('paired_cat_Attach')
                if paired_cat_Attach:
                    attachment_value = {
                        'name': paired_cat_Attach.filename,
                        'datas': base64.encodestring(paired_cat_Attach.read()),
                        'datas_fname': paired_cat_Attach.filename,
                        'res_model': 'crm.lead',
                        'res_id': bid_id.id,
                    }
                    attact_sudo.create(attachment_value)
                bid_id.sudo().set_oppor_stage_paired_catelog()
            elif contract_rcvd:
                contract_attach = kw.get('contract_attach')
                if contract_attach:
                    attachment_value = {
                        'name': contract_attach.filename,
                        'datas': base64.encodestring(contract_attach.read()),
                        'datas_fname': contract_attach.filename,
                        'res_model': 'crm.lead',
                        'res_id': bid_id.id,
                    }
                    attact_sudo.create(attachment_value)
                bid_id.sudo().set_oppor_stage_contract_received()
            url = bid_id.access_url
        return request.redirect(url)
