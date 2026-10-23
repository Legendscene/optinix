from flask import Flask
from .system import system_bp
from .optimization import optimization_bp
from .rollback import rollback_bp
from .network import network_bp
from .cleanup import cleanup_bp
from .services import services_bp
from .startup import startup_bp
from .registry import registry_bp
from .tweaks import tweaks_bp
from .debloat import debloat_bp
from .gaming import gaming_bp
from .bios import bios_bp
from .drivers import drivers_bp
from .memory import memory_bp
from .repair import repair_bp
from .speedtest import speedtest_bp
from .disk import disk_bp
from .toolbox import toolbox_bp
from .scheduler import scheduler_bp
from .background import background_bp
from .ai_api import ai_bp
from .files import files_bp
from .software import software_bp
from .power import power_bp
from .drivers_center import drivers_center_bp
from .plugins import plugins_bp
from .automation import automation_bp
from .devcenter import devcenter_bp
from .history_api import history_bp
from .intelligence_api import intelligence_bp
from .monitor_api import monitor_bp
from .diagnostics_api import diagnostics_bp
from .maintenance_api import maintenance_bp
from .reports_api import reports_bp
from .notifications_api import notifications_bp
from .timeline_api import timeline_bp
from .storage_api import storage_bp
from .device_info_api import device_info_bp
from .tools_api import tools_bp
from .marketplace_api import marketplace_bp
from .game_profiles_api import game_profiles_bp
from .game_library_api import game_library_bp
from .overview import overview_bp


def register_blueprints(app: Flask):
    app.register_blueprint(system_bp)
    app.register_blueprint(optimization_bp)
    app.register_blueprint(rollback_bp)
    app.register_blueprint(network_bp)
    app.register_blueprint(cleanup_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(startup_bp)
    app.register_blueprint(registry_bp)
    app.register_blueprint(tweaks_bp)
    app.register_blueprint(debloat_bp)
    app.register_blueprint(gaming_bp)
    app.register_blueprint(bios_bp)
    app.register_blueprint(drivers_bp)
    app.register_blueprint(memory_bp)
    app.register_blueprint(repair_bp)
    app.register_blueprint(speedtest_bp)
    app.register_blueprint(disk_bp)
    app.register_blueprint(toolbox_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(background_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(software_bp)
    app.register_blueprint(power_bp)
    app.register_blueprint(drivers_center_bp)
    app.register_blueprint(plugins_bp)
    app.register_blueprint(automation_bp)
    app.register_blueprint(devcenter_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(intelligence_bp)
    app.register_blueprint(monitor_bp)
    app.register_blueprint(diagnostics_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(storage_bp)
    app.register_blueprint(device_info_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(marketplace_bp)
    app.register_blueprint(game_profiles_bp)
    app.register_blueprint(game_library_bp)
    app.register_blueprint(overview_bp)
