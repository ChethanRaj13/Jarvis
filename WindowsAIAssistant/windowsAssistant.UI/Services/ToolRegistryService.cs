using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Services;

public class ToolRegistryService : IToolRegistry
{
    private readonly string _catalogPath;
    private readonly List<Tool> _tools = new();

    public ToolRegistryService(string? catalogPath = null)
    {
        _catalogPath = catalogPath ?? Path.Combine(System.AppContext.BaseDirectory, "Storage", "tools.json");
        LoadCatalog();
    }

    private void LoadCatalog()
    {
        if (!File.Exists(_catalogPath))
            return;

        var json = File.ReadAllText(_catalogPath);
        try
        {
            var list = JsonSerializer.Deserialize<List<Tool>>(json, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
            });
            if (list != null)
            {
                _tools.Clear();
                _tools.AddRange(list);
            }
        }
        catch
        {
            // ignore parse errors for now
        }
    }

    private void PersistCatalog()
    {
        var dir = Path.GetDirectoryName(_catalogPath) ?? ".";
        if (!Directory.Exists(dir))
            Directory.CreateDirectory(dir);

        var json = JsonSerializer.Serialize(_tools, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(_catalogPath, json);
    }

    public Task<IEnumerable<Tool>> GetAllAsync()
        => Task.FromResult<IEnumerable<Tool>>(_tools.ToList());

    public Task<Tool?> FindByIdAsync(string toolId)
        => Task.FromResult(_tools.FirstOrDefault(t => string.Equals(t.ToolId, toolId, System.StringComparison.OrdinalIgnoreCase)));

    public Task RegisterAsync(Tool tool)
    {
        _tools.RemoveAll(t => string.Equals(t.ToolId, tool.ToolId, System.StringComparison.OrdinalIgnoreCase));
        _tools.Add(tool);
        PersistCatalog();
        return Task.CompletedTask;
    }

    public Task UnregisterAsync(string toolId)
    {
        _tools.RemoveAll(t => string.Equals(t.ToolId, toolId, System.StringComparison.OrdinalIgnoreCase));
        PersistCatalog();
        return Task.CompletedTask;
    }

    public Task<IEnumerable<Tool>> ResolveCapabilityAsync(string capabilityId)
    {
        var matches = _tools.Where(t => t.Capabilities.Any(c => string.Equals(c.CapabilityId, capabilityId, System.StringComparison.OrdinalIgnoreCase)));
        return Task.FromResult<IEnumerable<Tool>>(matches.ToList());
    }

    public async Task<Tool?> SelectToolForCapabilityAsync(string capabilityId)
    {
        var candidates = (await ResolveCapabilityAsync(capabilityId)).ToList();
        if (!candidates.Any()) return null;

        // simple selector: prefer tools with status "Healthy" or "Available", then lowest risk
        var ordered = candidates.OrderByDescending(t => t.Status == "Healthy" || t.Status == "Available")
            .ThenBy(t => ParseRiskLevel(t.Metadata?.RiskLevel ?? "low"));

        return ordered.FirstOrDefault();
    }

    private int ParseRiskLevel(string risk)
    {
        return risk?.ToLower() switch
        {
            "low" => 1,
            "medium" => 2,
            "high" => 3,
            _ => 2,
        };
    }

    public Task<ToolHealth?> CheckHealthAsync(string toolId)
    {
        var tool = _tools.FirstOrDefault(t => string.Equals(t.ToolId, toolId, System.StringComparison.OrdinalIgnoreCase));
        if (tool == null) return Task.FromResult<ToolHealth?>(null);

        // Basic health check: rely on declared status
        var health = new ToolHealth
        {
            ToolId = tool.ToolId,
            IsHealthy = tool.Status == "Healthy" || tool.Status == "Available",
            Reason = tool.Status
        };

        return Task.FromResult<ToolHealth?>(health);
    }
}
