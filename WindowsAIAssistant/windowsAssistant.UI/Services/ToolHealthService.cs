using System.Threading.Tasks;

namespace windowsAssistant.UI.Services;

public class ToolHealthService
{
    private readonly IToolRegistry _registry;

    public ToolHealthService(IToolRegistry registry)
    {
        _registry = registry;
    }

    public Task<ToolHealth?> CheckAsync(string toolId)
        => _registry.CheckHealthAsync(toolId);
}
