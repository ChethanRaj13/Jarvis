using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Services;

public class ExecutionEngine
{
    public async Task<List<string>> ExecutePlanAsync(TaskExecutionPlan plan)
    {
        var logs = new List<string>();
        if (plan?.Steps == null || plan.Steps.Count == 0)
        {
            logs.Add("No execution steps were provided.");
            return logs;
        }

        int stepIndex = 0;
        foreach (var step in plan.Steps)
        {
            stepIndex++;
            var action = step.Action?.Trim() ?? string.Empty;
            if (string.IsNullOrEmpty(action))
            {
                continue;
            }

            string command;
            string description;
            if (!string.IsNullOrWhiteSpace(step.Command))
            {
                command = step.Command;
                description = "Backend-provided execution command";
            }
            else
            {
                var built = BuildCommand(action);
                command = built.command;
                description = built.description;
            }

            logs.Add($"Step {stepIndex}: {action}");
            logs.Add($"Command: {command}");
            logs.Add($"Description: {description}");

            var (success, output) = await RunPowerShellCommandAsync(command);
            logs.Add($"Result: {(success ? "succeeded" : "failed")}");
            if (!string.IsNullOrWhiteSpace(output))
            {
                logs.Add(output);
            }

            step.IsCompleted = success;
            if (!success)
            {
                logs.Add($"Execution halted after step {stepIndex} due to failure.");
                break;
            }
        }

        return logs;
    }

    public Task<string> VerifyPlanAsync(TaskExecutionPlan plan, string targetResource = ".")
    {
        if (plan?.Steps == null || plan.Steps.Count == 0)
        {
            return Task.FromResult("No verification steps were provided.");
        }

        var targetRoot = Path.GetFullPath(targetResource);
        var evidence = new List<string>();

        foreach (var step in plan.Steps)
        {
            var action = step.Action?.Trim() ?? string.Empty;
            if (string.IsNullOrEmpty(action))
            {
                continue;
            }

            if (IsFileCreation(action, out var pathCandidate))
            {
                var path = Path.Combine(targetRoot, pathCandidate ?? string.Empty);
                evidence.Add(File.Exists(path)
                    ? $"Verified file exists: {path}"
                    : $"Missing file: {path}");
            }
            else if (IsDirectoryCreation(action, out pathCandidate))
            {
                var path = Path.Combine(targetRoot, pathCandidate ?? string.Empty);
                evidence.Add(Directory.Exists(path)
                    ? $"Verified directory exists: {path}"
                    : $"Missing directory: {path}");
            }
            else
            {
                evidence.Add($"Verified action assumed: {action}");
            }
        }

        return Task.FromResult(string.Join("\n", evidence));
    }

    private static (string command, string description) BuildCommand(string step)
    {
        var normalized = step.Trim();
        var lower = normalized.ToLowerInvariant();

        if (lower.Contains("create") && lower.Contains("file"))
        {
            var targetName = ExtractTargetPath(normalized, "output.txt");
            return ($"New-Item -ItemType File -Path '{targetName}' -Force | Out-Null", "Create a file for the requested task");
        }

        if (lower.Contains("show") || lower.Contains("read") || lower.Contains("contents"))
        {
            return ("Get-ChildItem", "Inspect the current working directory contents");
        }

        if (lower.Contains("folder") || lower.Contains("directory"))
        {
            var targetName = ExtractTargetPath(normalized, "workspace");
            return ($"New-Item -ItemType Directory -Path '{targetName}' -Force | Out-Null", "Create a working directory");
        }

        return ($"Write-Output '{normalized}'", "Emit the requested action as a command");
    }

    private static bool IsFileCreation(string step, out string? targetPath)
    {
        var lower = step.ToLowerInvariant();
        if (lower.Contains("create") && lower.Contains("file"))
        {
            targetPath = ExtractTargetPath(step, "output.txt");
            return true;
        }

        targetPath = null;
        return false;
    }

    private static bool IsDirectoryCreation(string step, out string? targetPath)
    {
        var lower = step.ToLowerInvariant();
        if (lower.Contains("folder") || lower.Contains("directory"))
        {
            targetPath = ExtractTargetPath(step, "workspace");
            return true;
        }

        targetPath = null;
        return false;
    }

    private static string ExtractTargetPath(string step, string fallback)
    {
        var normalized = step.Trim();
        if (string.IsNullOrEmpty(normalized))
        {
            return fallback;
        }

        var match = Regex.Match(normalized, "named\\s+([^\\s,.;]+)", RegexOptions.IgnoreCase);
        if (match.Success)
        {
            return match.Groups[1].Value;
        }

        if (normalized.ToLowerInvariant().Contains("file"))
        {
            var candidate = normalized.Split(new[] { "file" }, StringSplitOptions.None)[1].Trim(' ', '.', ',', ';', ':');
            if (!string.IsNullOrEmpty(candidate))
            {
                return candidate;
            }
        }

        if (normalized.ToLowerInvariant().Contains("directory"))
        {
            var candidate = normalized.Split(new[] { "directory" }, StringSplitOptions.None)[1].Trim(' ', '.', ',', ';', ':');
            if (!string.IsNullOrEmpty(candidate))
            {
                return candidate;
            }
        }

        if (normalized.ToLowerInvariant().Contains("folder"))
        {
            var candidate = normalized.Split(new[] { "folder" }, StringSplitOptions.None)[1].Trim(' ', '.', ',', ';', ':');
            if (!string.IsNullOrEmpty(candidate))
            {
                return candidate;
            }
        }

        return fallback;
    }

    private static Task<(bool success, string output)> RunPowerShellCommandAsync(string command)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = "powershell",
            Arguments = $"-NoProfile -NonInteractive -Command \"{command}\"",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        using var process = new Process { StartInfo = startInfo };
        process.Start();
        var output = process.StandardOutput.ReadToEnd();
        var error = process.StandardError.ReadToEnd();
        process.WaitForExit();

        var combined = string.Join("\n", new[] { output?.Trim(), error?.Trim() });
        return Task.FromResult((process.ExitCode == 0, string.IsNullOrWhiteSpace(combined) ? "Command completed" : combined));
    }
}
