using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Services;

public class CapabilityResolver
{
    private readonly IToolRegistry _registry;

    public CapabilityResolver(IToolRegistry registry)
    {
        _registry = registry;
    }

    public Task<IEnumerable<Tool>> ResolveAsync(string capabilityId)
        => _registry.ResolveCapabilityAsync(capabilityId);
}
