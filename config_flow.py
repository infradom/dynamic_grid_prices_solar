"""Config flow for DynGridPricesSolar integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import json
import time
import xmltodict

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DOMAIN, NAME, CONF_NAME
from .const import CONF_ENTSOE_TOKEN, CONF_ENTSOE_AREA, CONF_ENTSOE_FACTOR_A, CONF_ENTSOE_FACTOR_B, CONF_ENTSOE_FACTOR_C, CONF_ENTSOE_FACTOR_D, CONF_ECOPWR_TOKEN
from .const import PLATFORMS
from .__init__ import EntsoeApiClient, EcopowerApiClient

_LOGGER = logging.getLogger(__name__)



class DynPricesFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        # Uncomment the next 2 lines if only a single instance of the integration is allowed:
        # if self._async_current_entries():
        #     return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            entsoe_token = user_input[CONF_ENTSOE_TOKEN]
            ecopwr_token = user_input[CONF_ECOPWR_TOKEN]
            valid1 = not entsoe_token or await self._test_credentials1( entsoe_token, user_input[CONF_ENTSOE_AREA] )
            valid2 = not ecopwr_token or await self._test_credentials2( ecopwr_token )
            valid = valid1 and valid2 and (ecopwr_token or entsoe_token)
            if valid:
                return self.async_create_entry( title=user_input[CONF_NAME], data=user_input )
            else:
                self._errors["base"] = "auth"
                _LOGGER.error("cannot authenticate auth - did you provide at least one API token?")

            return await self._show_config_form(user_input)

        user_input = {}
        # Provide defaults for form
        user_input[CONF_NAME]            = NAME
        user_input[CONF_ENTSOE_TOKEN]    = ""
        user_input[CONF_ENTSOE_AREA]     = '10YBE----------2'
        user_input[CONF_ENTSOE_FACTOR_A] = 0.001 *1.06 # scale to kWh
        user_input[CONF_ENTSOE_FACTOR_B] = 142.0 # per MWh
        user_input[CONF_ENTSOE_FACTOR_C] = 0.001 # scale to kWh
        user_input[CONF_ENTSOE_FACTOR_D] = 2.3   # per MWh
        user_input[CONF_ECOPWR_TOKEN]    = ""

        return await self._show_config_form(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DynPricesOptionsFlowHandler(config_entry)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit location data."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {   vol.Required(CONF_NAME,            default = user_input[CONF_NAME]): cv.string,
                    vol.Optional(CONF_ENTSOE_TOKEN,    default = user_input[CONF_ENTSOE_TOKEN]): cv.string,
                    vol.Required(CONF_ENTSOE_AREA,     default = user_input[CONF_ENTSOE_AREA]): cv.string,
                    vol.Required(CONF_ENTSOE_FACTOR_A, default = user_input[CONF_ENTSOE_FACTOR_A]): cv.positive_float,
                    vol.Required(CONF_ENTSOE_FACTOR_B, default = user_input[CONF_ENTSOE_FACTOR_B]): cv.positive_float,                    
                    vol.Required(CONF_ENTSOE_FACTOR_C, default = user_input[CONF_ENTSOE_FACTOR_C]): cv.positive_float,
                    vol.Required(CONF_ENTSOE_FACTOR_D, default = user_input[CONF_ENTSOE_FACTOR_D]): cv.positive_float,
                    vol.Optional(CONF_ECOPWR_TOKEN,    default = user_input[CONF_ECOPWR_TOKEN]): cv.string,
                }
            ),
            errors=self._errors,
        )

    async def _test_credentials1(self, token, area):
        """Return true if credentials is valid."""
        try:
            session = async_create_clientsession(self.hass)
            client = EntsoeApiClient(session, token, area)
            await client.async_get_data()
            return True
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error("entsoe credentials failed")
        return False
    
    async def _test_credentials2(self, token):
        """Return true if credentials is valid."""
        try:
            session = async_create_clientsession(self.hass)
            client = EcopowerApiClient(session, token)
            await client.async_get_data()
            return True
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error("ecopower credentials failed")
        return False


class DynPricesOptionsFlowHandler(config_entries.OptionsFlow):
    """Blueprint config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(x, default=self.options.get(x, True)): bool
                    for x in sorted(PLATFORMS)
                }
            ),
        )

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(
            title=self.config_entry.data.get(CONF_NAME), data=self.options
        )





