using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;
using windowsAssistant.UI.Models;
using windowsAssistant.UI.Services;

namespace windowsAssistant.UI.ViewModels;

public class ToolsViewModel : INotifyPropertyChanged
{
    private readonly ToolRegistryService _registry = new();

    public ObservableCollection<Tool> Tools { get; } = new();

    private bool _isLoading;
    public bool IsLoading
    {
        get => _isLoading;
        set { _isLoading = value; OnPropertyChanged(); }
    }

    public ToolsViewModel()
    {
        _ = LoadAsync();
    }

    public async Task LoadAsync()
    {
        IsLoading = true;
        Tools.Clear();
        var items = await _registry.GetAllAsync();
        foreach (var t in items)
            Tools.Add(t);
        IsLoading = false;
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    private void OnPropertyChanged([CallerMemberName] string? name = null) => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
