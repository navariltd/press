# Copyright (c) 2015, Web Notes and Contributors
# See license.txt

from __future__ import annotations

import unittest
from datetime import date, timedelta
from typing import TYPE_CHECKING

import frappe

from press.press.doctype.account_request.test_account_request import (
	create_test_account_request,
)
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.marketplace_app.test_marketplace_app import (
	create_test_marketplace_app,
)
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_plan_change.test_site_plan_change import create_test_plan

if TYPE_CHECKING:
	from press.press.doctype.drip_email.drip_email import DripEmail


def create_test_drip_email(
	send_after: int, saas_app: str | None = None, skip_sites_with_paid_plan: bool = False
) -> DripEmail:
	drip_email = frappe.get_doc(
		{
			"doctype": "Drip Email",
			"sender": "test@test.com",
			"sender_name": "Test User",
			"subject": "Drip Test",
			"message": "Drip Top, Drop Top",
			"send_after": send_after,
			"saas_app": saas_app,
			"skip_sites_with_paid_plan": skip_sites_with_paid_plan,
		}
	).insert(ignore_if_duplicate=True)
	drip_email.reload()
	return drip_email


class TestDripEmail(unittest.TestCase):
	def setUp(self) -> None:
		self.trial_site_plan = create_test_plan("Site", is_trial_plan=True)
		self.paid_site_plan = create_test_plan("Site", is_trial_plan=False)

	def tearDown(self):
		frappe.db.rollback()

	def test_correct_sites_are_selected_for_drip_email(self):
		test_app = create_test_app()
		test_marketplace_app = create_test_marketplace_app(test_app.name)

		drip_email = create_test_drip_email(0, saas_app=test_marketplace_app.name)

		site1 = create_test_site(
			"site1",
			standby_for=test_marketplace_app.name,
			account_request=create_test_account_request(
				"site1", saas=True, saas_app=test_marketplace_app.name
			).name,
		)
		site1.save()

		site2 = create_test_site("site2", account_request=create_test_account_request("site2").name)
		site2.save()

		create_test_site("site3")  # Note: site is not created

		self.assertEqual(drip_email.sites_to_send_drip, [site1.name])

	def test_older_site_isnt_selected(self):
		drip_email = create_test_drip_email(0)
		site = create_test_site("site1")
		site.account_request = create_test_account_request("site1", creation=date.today() - timedelta(1)).name
		site.save()
		self.assertNotEqual(drip_email.sites_to_send_drip, [site.name])

	def test_drip_emails_not_sent_to_sites_with_paid_plan_having_special_flag(self):
		"""
		If you enable `skip_sites_with_paid_plan` flag, drip emails should not be sent to sites with paid plan set
		No matter whether they have paid for any invoice or not
		"""
		test_app = create_test_app()
		test_marketplace_app = create_test_marketplace_app(test_app.name)

		drip_email = create_test_drip_email(
			0, saas_app=test_marketplace_app.name, skip_sites_with_paid_plan=True
		)

		site1 = create_test_site(
			"site1",
			standby_for=test_marketplace_app.name,
			account_request=create_test_account_request(
				"site1", saas=True, saas_app=test_marketplace_app.name
			).name,
			plan=self.trial_site_plan.name,
		)
		site1.save()

		site2 = create_test_site(
			"site2",
			standby_for=test_marketplace_app.name,
			account_request=create_test_account_request(
				"site2", saas=True, saas_app=test_marketplace_app.name
			).name,
			plan=self.paid_site_plan.name,
		)
		site2.save()

		site3 = create_test_site(
			"site3",
			standby_for=test_marketplace_app.name,
			account_request=create_test_account_request(
				"site3", saas=True, saas_app=test_marketplace_app.name
			).name,
			plan=self.trial_site_plan.name,
		)
		site3.save()

		self.assertEqual(drip_email.sites_to_send_drip, [site1.name, site3.name])
