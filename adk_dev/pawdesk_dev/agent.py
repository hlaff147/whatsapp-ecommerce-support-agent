"""Expõe `root_agent` conectado a dados sintéticos em memória para `adk web` e `adk eval`."""

from pawdesk.bootstrap.container import Container
from pawdesk.bootstrap.settings import Settings

_dev_settings = Settings(
    storage_backend="memory",
    adk_session_backend="memory",
    channel_mode="console",
    helpdesk_mode="fake",
)

root_agent = Container(_dev_settings).build_for_dev().root_agent
