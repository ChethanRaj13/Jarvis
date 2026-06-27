using System;
using System.Collections.Generic;
using System.Linq;
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

    private readonly List<ChatMessage> chatHistory = new();
    private List<PlanStep> currentPlan = new();
    private List<ExecutionCommand> currentCommands = new();

    public MainWindow()
    {
        InitializeComponent();

        runtimeStateStore = new RuntimeStateStore();
        lifecycleManager = new LifecycleManager(runtimeStateStore);
        taskCoordinator = new TaskCoordinator(new TaskQueue(), lifecycleManager, runtimeStateStore);
        taskManager = new TaskManager(taskCoordinator, lifecycleManager, runtimeStateStore, new ExecutionEngine());
    }

    private async void SendButton_Click(object sender, RoutedEventArgs e)
    {
        string userMessage = CommandInput.Text;

        if (string.IsNullOrWhiteSpace(userMessage))
            return;

        chatHistory.Add(new ChatMessage
        {
            Sender = "User",
            Content = userMessage
        });

        TextBlock messageBlock = new TextBlock
        {
            Text = "User: " + userMessage,
            Foreground = Brushes.White,
            FontSize = 16,
            Margin = new Thickness(0, 10, 0, 10),
            TextWrapping = TextWrapping.Wrap
        };

        ChatPanel.Children.Add(messageBlock);
        CommandInput.Clear();

        SendButton.IsEnabled = false;
        CommandInput.IsEnabled = false;

        try
        {
            currentPlan = await planningService.GeneratePlanAsync(userMessage);

            string assistantReply = string.Join("\n", currentPlan);

            chatHistory.Add(new ChatMessage
            {
                Sender = "Assistant",
                Content = assistantReply
            });

            TextBlock assistantHeader = new TextBlock
            {
                Text = "Assistant: Execution Plan",
                Foreground = Brushes.LightBlue,
                FontSize = 16,
                FontWeight = FontWeights.Bold,
                Margin = new Thickness(0, 10, 0, 10)
            };

            ChatPanel.Children.Add(assistantHeader);

            foreach (var step in currentPlan)
            {
                var displayText = step.StepNumber > 0
                    ? $"{step.StepNumber}. {step.Action}"
                    : step.Action;

                TextBlock stepBlock = new TextBlock
                {
                    Text = "• " + displayText,
                    Foreground = Brushes.LightBlue,
                    FontSize = 14,
                    Margin = new Thickness(20, 2, 0, 2),
                    TextWrapping = TextWrapping.Wrap
                };

                ChatPanel.Children.Add(stepBlock);

                if (!string.IsNullOrWhiteSpace(step.ToolOrMethod))
                {
                    var hintBlock = new TextBlock
                    {
                        Text = $"  Tool hint: {step.ToolOrMethod}",
                        Foreground = Brushes.LightSkyBlue,
                        FontSize = 12,
                        Margin = new Thickness(40, 0, 0, 4),
                        TextWrapping = TextWrapping.Wrap
                    };
                    ChatPanel.Children.Add(hintBlock);
                }
            }

            try
            {
                var executionResponse = await executionService.GenerateExecutionPlanAsync(currentPlan.Select(step => step.Action).ToList());
                currentCommands = executionResponse.Commands;

                if (currentCommands.Count > 0)
                {
                    var header = new TextBlock
                    {
                        Text = "Assistant: Generated execution commands",
                        Foreground = Brushes.LightCyan,
                        FontSize = 16,
                        FontWeight = FontWeights.Bold,
                        Margin = new Thickness(0, 12, 0, 10)
                    };
                    ChatPanel.Children.Add(header);

                    foreach (var command in currentCommands)
                    {
                        var commandBlock = new TextBlock
                        {
                            Text = $"• Command: {command.Command}",
                            Foreground = Brushes.LightCyan,
                            FontSize = 14,
                            Margin = new Thickness(20, 2, 0, 2),
                            TextWrapping = TextWrapping.Wrap
                        };
                        ChatPanel.Children.Add(commandBlock);

                        var toolBlock = new TextBlock
                        {
                            Text = $"  Selected tool: {command.Tool ?? "powershell"} - {command.Description}",
                            Foreground = Brushes.LightCyan,
                            FontSize = 12,
                            Margin = new Thickness(40, 0, 0, 6),
                            TextWrapping = TextWrapping.Wrap
                        };
                        ChatPanel.Children.Add(toolBlock);
                    }
                }
                else
                {
                    currentCommands = new List<ExecutionCommand>();
                }
            }
            catch (Exception ex)
            {
                var errorBlock = new TextBlock
                {
                    Text = "Assistant: Failed to generate execution commands: " + ex.Message,
                    Foreground = Brushes.OrangeRed,
                    FontSize = 14,
                    Margin = new Thickness(0, 10, 0, 10),
                    TextWrapping = TextWrapping.Wrap
                };
                ChatPanel.Children.Add(errorBlock);
                TaskStatusText.Text = "Command generation failed";
                ApproveButton.Visibility = Visibility.Collapsed;
                return;
            }

            TaskNameText.Text = userMessage;
            TaskStatusText.Text = "Planning";

            ProgressPanel.Visibility = Visibility.Visible;

            TaskProgressBar.Value = 25;
            ProgressText.Text = "25%";

            ApproveButton.Visibility = Visibility.Visible;
        }
        catch (Exception ex)
        {
            TextBlock errorBlock = new TextBlock
            {
                Text = "Assistant: " + ex.Message,
                Foreground = Brushes.OrangeRed,
                FontSize = 14,
                Margin = new Thickness(0, 10, 0, 10),
                TextWrapping = TextWrapping.Wrap
            };
            ChatPanel.Children.Add(errorBlock);
            TaskStatusText.Text = "Backend unavailable";
            ProgressPanel.Visibility = Visibility.Collapsed;
        }
        finally
        {
            SendButton.IsEnabled = true;
            CommandInput.IsEnabled = true;
        }
    }

    private async void ApproveButton_Click(object sender, RoutedEventArgs e)
    {
        if (currentPlan == null || currentPlan.Count == 0)
        {
            TaskStatusText.Text = "No plan available";
            return;
        }

        TaskStatusText.Text = "Executing";

        TaskProgressBar.Value = 50;
        ProgressText.Text = "50%";

        try
        {
            var taskPlan = new TaskExecutionPlan
            {
                Steps = currentPlan.Select((step, index) => new TaskStep
                {
                    StepNumber = step.StepNumber > 0 ? step.StepNumber : index + 1,
                    Action = step.Action,
                    Command = currentCommands.ElementAtOrDefault(index)?.Command,
                    ToolId = !string.IsNullOrWhiteSpace(step.ToolOrMethod)
                        ? step.ToolOrMethod
                        : currentCommands.ElementAtOrDefault(index)?.Tool,
                    IsCompleted = false
                }).ToList()
            };

            var taskItem = await taskManager.CreateTaskAsync(taskPlan, new TaskContext { Metadata = { ["source"] = "UI" } });
            var logs = await taskManager.ExecuteTaskAsync(taskItem);

            foreach (var log in logs)
            {
                TextBlock logBlock = new TextBlock
                {
                    Text = "Assistant: " + log,
                    Foreground = Brushes.LightGreen,
                    FontSize = 16,
                    Margin = new Thickness(0, 8, 0, 8),
                    TextWrapping = TextWrapping.Wrap
                };

                ChatPanel.Children.Add(logBlock);
            }

            var verificationSummary = await taskManager.VerifyTaskAsync(taskItem, TaskNameText.Text);
            TextBlock verificationBlock = new TextBlock
            {
                Text = "Assistant: Verification -> " + verificationSummary,
                Foreground = Brushes.LightSkyBlue,
                FontSize = 14,
                Margin = new Thickness(0, 8, 0, 8),
                TextWrapping = TextWrapping.Wrap
            };

            ChatPanel.Children.Add(verificationBlock);

            TaskProgressBar.Value = 100;
            ProgressText.Text = "100%";

            TaskStatusText.Text = "Completed";
        }
        catch (Exception ex)
        {
            TextBlock errorBlock = new TextBlock
            {
                Text = "Assistant: " + ex.Message,
                Foreground = Brushes.OrangeRed,
                FontSize = 14,
                Margin = new Thickness(0, 8, 0, 8),
                TextWrapping = TextWrapping.Wrap
            };
            ChatPanel.Children.Add(errorBlock);
            TaskStatusText.Text = "Execution failed";
        }

        ApproveButton.Visibility = Visibility.Collapsed;
    }
}