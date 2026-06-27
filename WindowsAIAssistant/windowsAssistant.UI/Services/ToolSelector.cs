using System.Threading.Tasks;

namespace windowsAssistant.UI.Services;

public class ToolSelector
{
    private readonly IToolRegistry _registry;

    public ToolSelector(IToolRegistry registry)
    {
        _registry = registry;
    }

    public Task<Models.Tool?> SelectPrimaryAsync(string capabilityId)
        => _registry.SelectToolForCapabilityAsync(capabilityId);
}
