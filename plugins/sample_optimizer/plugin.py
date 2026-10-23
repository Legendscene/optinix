from core.plugin_system import PluginBase, PluginMetadata

class SampleOptimizerPlugin(PluginBase):
    def get_metadata(self):
        return PluginMetadata(
            name="Sample Optimizer",
            version="1.0.0",
            author="Optinix",
            description="A sample plugin that demonstrates the plugin system"
        )
    def initialize(self):
        return True
    def on_optimize(self):
        return [{"success": True, "message": "Sample optimization complete"}]
