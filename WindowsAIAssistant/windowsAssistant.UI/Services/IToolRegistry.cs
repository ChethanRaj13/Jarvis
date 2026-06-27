using System.Collections.Generic;
using System.Threading.Tasks;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Services;

public interface IToolRegistry
{
    Task<IEnumerable<Tool>> GetAllAsync();
    Task<Tool?> FindByIdAsync(string toolId);
    Task RegisterAsync(Tool tool);
    Task UnregisterAsync(string toolId);
    Task<IEnumerable<Tool>> ResolveCapabilityAsync(string capabilityId);
    Task<Tool?> SelectToolForCapabilityAsync(string capabilityId);
    Task<ToolHealth?> CheckHealthAsync(string toolId);
}

public class ToolHealth
{
    public string ToolId { get; set; } = string.Empty;
    public bool IsHealthy { get; set; }
    public string Reason { get; set; } = string.Empty;
}
