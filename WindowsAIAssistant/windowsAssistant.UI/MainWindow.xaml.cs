using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using windowsAssistant.UI.Models;
using windowsAssistant.UI.Services;

namespace windowsAssistant.UI;

public partial class MainWindow : Window
{
    private readonly PlanningService planningService = new();
    private readonly ExecutionService executionService = new();
    private readonly VerificationService verificationService = new();
    private readonly ToolRegistryService toolRegistryService = new();
    private readonly TaskManager taskManager;
    private readonly TaskCoordinator taskCoordinator;
    private readonly LifecycleManager lifecycleManager;
    private readonly RuntimeStateStore runtimeStateStore;
    private bool isInitialized;

    // Pending approval fields
    private bool isApprovalPending = false;
    private string pendingTaskType = string.Empty;
    private string pendingTaskText = string.Empty;
    private string pendingFileSearchQuery = string.Empty;
    private string pendingCalendarSummary = string.Empty;
    private string pendingCalendarDate = string.Empty;
    private string pendingCalendarTime = string.Empty;
    private string pendingCalendarDescription = string.Empty;

    private readonly List<ChatMessage> chatHistory = new();
    private List<PlanStep> currentPlan = new();
    private List<PlanStep> currentActionableSteps = new();
    private List<ExecutionCommand> currentCommands = new();

    public MainWindow()
    {
        InitializeComponent();

        runtimeStateStore = new RuntimeStateStore();
        lifecycleManager = new LifecycleManager(runtimeStateStore);
        taskCoordinator = new TaskCoordinator(new TaskQueue(), lifecycleManager, runtimeStateStore);
        taskManager = new TaskManager(taskCoordinator, lifecycleManager, runtimeStateStore, new ExecutionEngine());

        isInitialized = true;
        UpdateInputModeUI();
    }

    private void TaskTypeComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        UpdateInputModeUI();
    }

    private async void ParseCalendarButton_Click(object sender, RoutedEventArgs e)
    {
        var prompt = CalendarPromptInput.Text?.Trim() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(prompt))
        {
            TaskStatusText.Text = "Please enter calendar event details to parse.";
            return;
        }

        try
        {
            TaskStatusText.Text = "Parsing calendar event...";
            var result = await executionService.ParseCalendarFieldsAsync(prompt);
            CalendarSummaryInput.Text = result.Message;
            CalendarDateInput.Text = result.Date;
            CalendarTimeInput.Text = result.Time;
            CalendarDescriptionInput.Text = result.Description;
            TaskStatusText.Text = "Parsed calendar event. Review the fields before execution.";
        }
        catch (Exception ex)
        {
            TaskStatusText.Text = "Failed to parse calendar event: " + ex.Message;
        }
    }

    private async void SearchFileButton_Click(object sender, RoutedEventArgs e)
    {
        var query = FileSearchInput?.Text?.Trim() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(query))
        {
            TaskStatusText.Text = "Please enter a file name or partial name to search for.";
            return;
        }

        await PerformFileSearchAsync(query);
    }

    private async void FileSearchSample_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button)
        {
            var query = button.Content?.ToString() ?? string.Empty;
            if (FileSearchInput != null)
            {
                FileSearchInput.Text = query;
            }
            await PerformFileSearchAsync(query);
        }
    }

    private async Task PerformFileSearchAsync(string query)
    {
        try
        {
            TaskStatusText.Text = "Searching files...";
            var engine = new ExecutionEngine();
            var root = Path.GetFullPath(AppContext.BaseDirectory ?? Directory.GetCurrentDirectory());
            var results = await engine.SearchFilesAsync(query, root);
            if (FileSearchResults != null)
            {
                FileSearchResults.ItemsSource = results;
            }

            TaskStatusText.Text = results.Count == 0 ? "No files found." : $"Found {results.Count} file(s).";
        }
        catch (Exception ex)
        {
            TaskStatusText.Text = "File search failed: " + ex.Message;
        }
    }

    private void UpdateInputModeUI()
    {
        if (!isInitialized || TaskTypeComboBox == null)
        {
            return;
        }

        var selectedItem = TaskTypeComboBox.SelectedItem as ComboBoxItem;
        var taskType = selectedItem?.Content?.ToString() ?? "Normal";
        var isCalendar = taskType.Equals("Calendar", StringComparison.OrdinalIgnoreCase);
        var isFileSearch = taskType.Equals("File Search", StringComparison.OrdinalIgnoreCase);

        if (TaskDetailsInput != null)
        {
            TaskDetailsInput.Visibility = isCalendar ? Visibility.Collapsed : Visibility.Visible;
        }

        if (CalendarFormPanel != null)
        {
            CalendarFormPanel.Visibility = isCalendar ? Visibility.Visible : Visibility.Collapsed;
        }

        if (FileSearchPanel != null)
        {
            FileSearchPanel.Visibility = isFileSearch ? Visibility.Visible : Visibility.Collapsed;
        }

        if (CalendarPromptInput != null)
        {
            CalendarPromptInput.Clear();
        }

        if (CalendarSummaryInput != null)
        {
            CalendarSummaryInput.Clear();
        }

        if (CalendarDateInput != null)
        {
            CalendarDateInput.Clear();
        }

        if (CalendarTimeInput != null)
        {
            CalendarTimeInput.Clear();
        }

        if (CalendarDescriptionInput != null)
        {
            CalendarDescriptionInput.Clear();
        }

        if (FileSearchInput != null)
        {
            FileSearchInput.Clear();
        }

        if (FileSearchResults != null)
        {
            FileSearchResults.ItemsSource = null;
        }

        if (TaskStatusText != null)
        {
            TaskStatusText.Text = string.Empty;
        }
    }

    private async void SendButton_Click(object sender, RoutedEventArgs e)
    {
        if (isApprovalPending)
        {
            TaskStatusText.Text = "Please approve the pending task before sending a new one.";
            return;
        }

        var selectedItem = TaskTypeComboBox.SelectedItem as ComboBoxItem;
        var taskType = selectedItem?.Content?.ToString() ?? "Normal";
        var taskText = TaskDetailsInput.Text?.Trim() ?? string.Empty;

        if (taskType.Equals("File Search", StringComparison.OrdinalIgnoreCase))
        {
            var query = TaskDetailsInput?.Text?.Trim();
            if (string.IsNullOrWhiteSpace(query)) query = FileSearchInput?.Text?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(query))
            {
                TaskStatusText.Text = "Please enter a file name to search for.";
                return;
            }

            StageApproval(taskType, taskText, query);
            return;
        }

        if (taskType.Equals("Calendar", StringComparison.OrdinalIgnoreCase))
        {
            taskText = CalendarPromptInput?.Text?.Trim() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(taskText))
            {
                TaskStatusText.Text = "Please enter calendar event details.";
                return;
            }
        }

        if (taskType.Equals("Normal", StringComparison.OrdinalIgnoreCase) &&
            taskText.Contains("flutter", StringComparison.OrdinalIgnoreCase) &&
            taskText.Contains("setup", StringComparison.OrdinalIgnoreCase))
        {
            StageApproval(taskType, taskText);
            return;
        }

        if (string.IsNullOrWhiteSpace(taskText))
        {
            TaskStatusText.Text = "Please enter task details.";
            return;
        }

        var calendarSummary = CalendarSummaryInput?.Text?.Trim() ?? string.Empty;
        var calendarDate = CalendarDateInput?.Text?.Trim() ?? string.Empty;
        var calendarTime = CalendarTimeInput?.Text?.Trim() ?? string.Empty;
        var calendarDescription = CalendarDescriptionInput?.Text?.Trim() ?? string.Empty;

        if (taskType.Equals("Calendar", StringComparison.OrdinalIgnoreCase) &&
            (string.IsNullOrWhiteSpace(calendarSummary) || string.IsNullOrWhiteSpace(calendarDate) || string.IsNullOrWhiteSpace(calendarTime)))
        {
            var parsed = executionService.ParseCalendarFieldsLocally(taskText);
            calendarSummary = parsed.Message;
            calendarDate = parsed.Date;
            calendarTime = parsed.Time;
            calendarDescription = parsed.Description;

            if (CalendarSummaryInput != null)
            {
                CalendarSummaryInput.Text = calendarSummary;
            }
            if (CalendarDateInput != null)
            {
                CalendarDateInput.Text = calendarDate;
            }
            if (CalendarTimeInput != null)
            {
                CalendarTimeInput.Text = calendarTime;
            }
            if (CalendarDescriptionInput != null)
            {
                CalendarDescriptionInput.Text = calendarDescription;
            }
        }

        StageApproval(taskType, taskText, string.Empty, calendarSummary, calendarDate, calendarTime, calendarDescription);
    }

    private void StageApproval(
        string taskType,
        string taskText,
        string fileSearchQuery = "",
        string calendarSummary = "",
        string calendarDate = "",
        string calendarTime = "",
        string calendarDescription = "")
    {
        isApprovalPending = true;
        pendingTaskType = taskType;
        pendingTaskText = taskText;
        pendingFileSearchQuery = fileSearchQuery;
        pendingCalendarSummary = calendarSummary;
        pendingCalendarDate = calendarDate;
        pendingCalendarTime = calendarTime;
        pendingCalendarDescription = calendarDescription;

        ApproveButton.Visibility = Visibility.Visible;
        ApproveButton.IsEnabled = true;
        SendButton.IsEnabled = false;
        TaskStatusText.Text = "Task ready for approval. Click Approve to execute.";
        AddChatMessage("Assistant", "Task is pending approval before execution.", Brushes.LightSkyBlue, new SolidColorBrush(Color.FromRgb(12, 31, 53)));
    }

    private void ClearPendingApproval()
    {
        isApprovalPending = false;
        pendingTaskType = string.Empty;
        pendingTaskText = string.Empty;
        pendingFileSearchQuery = string.Empty;
        pendingCalendarSummary = string.Empty;
        pendingCalendarDate = string.Empty;
        pendingCalendarTime = string.Empty;
        pendingCalendarDescription = string.Empty;

        ApproveButton.Visibility = Visibility.Collapsed;
        ApproveButton.IsEnabled = false;
        SendButton.IsEnabled = true;
    }

    private async Task ExecutePendingTaskAsync()
    {
        try
        {
            TaskStatusText.Text = "Executing approved task...";
            ShowLoadingOverlay(true);
            ApproveButton.IsEnabled = false;

            if (pendingTaskType.Equals("File Search", StringComparison.OrdinalIgnoreCase))
            {
                var query = pendingFileSearchQuery;
                var engine = new ExecutionEngine();
                var root = Path.GetFullPath(AppContext.BaseDirectory ?? Directory.GetCurrentDirectory());
                var results = await engine.SearchFilesAsync(query, root);

                if (FileSearchResults != null)
                {
                    FileSearchResults.ItemsSource = results;
                }

                if (results == null || results.Count == 0)
                {
                    AddChatMessage("Assistant", "No files found matching: " + query, Brushes.LightGreen, new SolidColorBrush(Color.FromRgb(15, 23, 42)));
                    TaskStatusText.Text = "No files found.";
                }
                else
                {
                    var summary = $"Found {results.Count} file(s) matching '{query}':\n" + string.Join("\n", results.Take(20));
                    AddChatMessage("Assistant", summary, Brushes.LightGreen, new SolidColorBrush(Color.FromRgb(15, 23, 42)));
                    TaskStatusText.Text = $"Found {results.Count} file(s).";
                }

                return;
            }

            if (pendingTaskType.Equals("Normal", StringComparison.OrdinalIgnoreCase) &&
                pendingTaskText.Contains("flutter", StringComparison.OrdinalIgnoreCase) &&
                pendingTaskText.Contains("setup", StringComparison.OrdinalIgnoreCase))
            {
                AddChatMessage("Assistant", "Flutter setup execution flow:\n1. Verify Flutter installation with `flutter --version`.\n2. Run `flutter doctor` to identify missing dependencies.\n3. Install any required Android/iOS tooling and accept licenses.\n4. Set up device/emulator or connect a physical device.\n5. Run `flutter create my_app` to scaffold a new project.\n6. Open the project in your editor and run `flutter run`.\n7. Confirm the sample app launches successfully.", Brushes.LightGreen, new SolidColorBrush(Color.FromRgb(15, 23, 42)));
                TaskStatusText.Text = "Flutter setup plan displayed.";
                return;
            }

            var taskType = pendingTaskType;
            var taskText = pendingTaskText;

            chatHistory.Add(new ChatMessage
            {
                Sender = "User",
                Content = taskText
            });

            AddChatMessage($"User ({taskType})", taskText, Brushes.White, new SolidColorBrush(Color.FromRgb(17, 24, 39)));

            if (taskType.Equals("Normal", StringComparison.OrdinalIgnoreCase))
            {
                TaskDetailsInput?.Clear();
            }

            SendButton.IsEnabled = false;
            TaskDetailsInput?.SetCurrentValue(IsEnabledProperty, false);
            CalendarPromptInput?.SetCurrentValue(IsEnabledProperty, false);
            CalendarSummaryInput?.SetCurrentValue(IsEnabledProperty, false);
            CalendarDateInput?.SetCurrentValue(IsEnabledProperty, false);
            CalendarTimeInput?.SetCurrentValue(IsEnabledProperty, false);
            CalendarDescriptionInput?.SetCurrentValue(IsEnabledProperty, false);
            ParseCalendarButton?.SetCurrentValue(IsEnabledProperty, false);
            TaskTypeComboBox?.SetCurrentValue(IsEnabledProperty, false);
            ShowLoadingOverlay(true);

            var command = taskType.Equals("Calendar", StringComparison.OrdinalIgnoreCase)
                ? $"CALENDAR_EVENT:{pendingCalendarSummary} at {pendingCalendarDate} {pendingCalendarTime} | {pendingCalendarDescription}"
                : $"Write-Output '{taskText.Replace("'", "''")}'";

            var tool = taskType.Equals("Calendar", StringComparison.OrdinalIgnoreCase)
                ? "calendar"
                : "powershell";

            var taskPlan = new TaskExecutionPlan
            {
                Steps = new List<TaskStep>
                {
                    new TaskStep
                    {
                        StepNumber = 1,
                        Action = taskText,
                        Command = command,
                        ToolId = tool,
                        IsCompleted = false
                    }
                }
            };

            TaskNameText.Text = taskText;
            TaskStatusText.Text = "Executing";
            ProgressPanel.Visibility = Visibility.Visible;
            TaskProgressBar.Value = 20;
            ProgressText.Text = "20%";

            var taskItem = await taskManager.CreateTaskAsync(taskPlan, new TaskContext { Metadata = { ["source"] = "UI local" } });
            var logs = await taskManager.ExecuteTaskAsync(taskItem);

            foreach (var log in logs)
            {
                AddChatMessage("Assistant", log, Brushes.LightGreen, new SolidColorBrush(Color.FromRgb(15, 23, 42)));
            }

            var verificationSummary = await taskManager.VerifyTaskAsync(taskItem, TaskNameText.Text);
            AddChatMessage("Verification", verificationSummary, Brushes.LightSkyBlue, new SolidColorBrush(Color.FromRgb(12, 31, 53)));

            TaskProgressBar.Value = 100;
            ProgressText.Text = "100%";
            TaskStatusText.Text = "Completed";
        }
        catch (Exception ex)
        {
            AddChatMessage("Assistant", ex.Message, Brushes.OrangeRed, new SolidColorBrush(Color.FromRgb(53, 18, 18)));
            TaskStatusText.Text = "Execution failed";
        }
        finally
        {
            SendButton.IsEnabled = true;
            TaskDetailsInput?.SetCurrentValue(IsEnabledProperty, true);
            CalendarPromptInput?.SetCurrentValue(IsEnabledProperty, true);
            CalendarSummaryInput?.SetCurrentValue(IsEnabledProperty, true);
            CalendarDateInput?.SetCurrentValue(IsEnabledProperty, true);
            CalendarTimeInput?.SetCurrentValue(IsEnabledProperty, true);
            CalendarDescriptionInput?.SetCurrentValue(IsEnabledProperty, true);
            ParseCalendarButton?.SetCurrentValue(IsEnabledProperty, true);
            TaskTypeComboBox?.SetCurrentValue(IsEnabledProperty, true);
            ShowLoadingOverlay(false);
        }
    }

    private void ShowLoadingOverlay(bool show)
    {
        LoadingOverlay.Visibility = show ? Visibility.Visible : Visibility.Collapsed;
    }

    private void AddChatMessage(string sender, string content, Brush foreground, Brush background)
    {
        var message = string.IsNullOrWhiteSpace(content) ? "(no output)" : content.Trim();
        var card = new Border
        {
            Background = background,
            BorderBrush = new SolidColorBrush(Color.FromRgb(51, 65, 85)),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(8),
            Padding = new Thickness(12),
            Margin = new Thickness(0, 0, 0, 10),
            Child = new StackPanel
            {
                Children =
                {
                    new TextBlock
                    {
                        Text = sender,
                        Foreground = Brushes.LightGray,
                        FontSize = 12,
                        FontWeight = FontWeights.SemiBold,
                        Margin = new Thickness(0, 0, 0, 5)
                    },
                    new TextBlock
                    {
                        Text = message,
                        Foreground = foreground,
                        FontSize = 14,
                        TextWrapping = TextWrapping.Wrap
                    }
                }
            }
        };

        ChatPanel.Children.Add(card);
    }

    private async void ApproveButton_Click(object sender, RoutedEventArgs e)
    {
        if (!isApprovalPending)
        {
            TaskStatusText.Text = "No pending task is waiting for approval.";
            ApproveButton.Visibility = Visibility.Collapsed;
            return;
        }

        await ExecutePendingTaskAsync();
        ClearPendingApproval();
    }
}
