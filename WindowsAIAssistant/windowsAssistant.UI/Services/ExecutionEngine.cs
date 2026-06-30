using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using windowsAssistant.UI.Models;
using System.Linq;

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

            var toolName = ResolveToolName(step, command, action);
            var startedAt = DateTimeOffset.UtcNow;
            logs.Add($"Step {stepIndex}: {action}");
            logs.Add($"Step Number: {stepIndex}");
            logs.Add($"Tool: {toolName}");
            logs.Add($"Command: {command}");
            logs.Add($"Description: {description}");
            logs.Add($"Start Time: {startedAt:O}");

            bool success;
            string output;
            int exitCode;
            string failureReason = string.Empty;
            try
            {
                switch (toolName.ToLowerInvariant())
                {
                    case "calendar":
                        (success, output, exitCode) = await ExecuteCalendarEventAsync(command, action);
                        break;
                    case "flutter":
                        (success, output, exitCode) = await RunFlutterCommandAsync(command);
                        break;
                    case "git":
                        (success, output, exitCode) = await RunGitCommandAsync(command);
                        break;
                    case "cmd":
                        (success, output, exitCode) = await RunCmdCommandAsync(command);
                        break;
                    case "powershell":
                    default:
                        (success, output, exitCode) = await RunPowerShellCommandAsync(command);
                        break;
                }
            }
            catch (Exception ex)
            {
                success = false;
                output = ex.Message;
                exitCode = -1;
                failureReason = ex.Message;
            }

            var completedAt = DateTimeOffset.UtcNow;
            var duration = completedAt - startedAt;
            logs.Add($"End Time: {completedAt:O}");
            logs.Add($"Duration: {duration.TotalSeconds:F2}s");
            logs.Add($"Exit Code: {exitCode}");
            logs.Add($"Success: {success}");
            if (!success)
            {
                var failureMessage = string.IsNullOrWhiteSpace(failureReason) ? output : failureReason;
                logs.Add($"Failure Reason: {failureMessage}");
            }
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

    public async Task<List<string>> SearchFilesAsync(string pattern, string rootPath = ".")
    {
        return await Task.Run(() =>
        {
            var results = new List<string>();
            try
            {
                var root = string.IsNullOrWhiteSpace(rootPath) ? GetDefaultSearchRoot() : Path.GetFullPath(rootPath);
                if (!Directory.Exists(root))
                {
                    root = GetDefaultSearchRoot();
                }

                // If the file isn't found under the current root, try the candidate project roots too.
                foreach (var candidateRoot in GetSearchRoots(root))
                {
                    foreach (var f in EnumerateFilesSafe(candidateRoot))
                    {
                        try
                        {
                            if (Path.GetFileName(f).IndexOf(pattern, StringComparison.OrdinalIgnoreCase) >= 0)
                            {
                                results.Add(f);
                                if (results.Count >= 200) break;
                            }
                        }
                        catch
                        {
                            // ignore per-file access issues
                        }
                    }

                    if (results.Count >= 200)
                    {
                        break;
                    }
                }
            }
            catch (UnauthorizedAccessException)
            {
                // return empty or partial results
            }
            catch (Exception)
            {
                // swallow and return what we have
            }

            return results;
        });
    }

    private static string GetDefaultSearchRoot()
    {
        var candidate = AppContext.BaseDirectory;
        if (!string.IsNullOrWhiteSpace(candidate) && Directory.Exists(candidate))
        {
            return Path.GetFullPath(candidate);
        }

        candidate = Environment.CurrentDirectory;
        if (!string.IsNullOrWhiteSpace(candidate) && Directory.Exists(candidate))
        {
            return Path.GetFullPath(candidate);
        }

        return Path.GetPathRoot(Environment.SystemDirectory) ?? ".";
    }

    private static IEnumerable<string> GetSearchRoots(string initialRoot)
    {
        var roots = new List<string> { initialRoot };
        var directory = new DirectoryInfo(initialRoot);
        for (var depth = 0; depth < 6 && directory?.Parent != null; depth++)
        {
            directory = directory.Parent;
            if (directory == null)
            {
                break;
            }

            roots.Add(directory.FullName);
            if (directory.GetFiles("windowsAssistant.UI.csproj", SearchOption.TopDirectoryOnly).Any()
                || directory.GetFiles("*.sln", SearchOption.TopDirectoryOnly).Any())
            {
                break;
            }
        }

        return roots.Distinct(StringComparer.OrdinalIgnoreCase);
    }

    private static IEnumerable<string> EnumerateFilesSafe(string root)
    {
        var directories = new Stack<string>();
        directories.Push(root);

        while (directories.Count > 0)
        {
            var current = directories.Pop();
            string[] subDirs;
            try
            {
                subDirs = Directory.GetDirectories(current);
            }
            catch
            {
                continue;
            }

            foreach (var dir in subDirs)
            {
                directories.Push(dir);
            }

            string[] files;
            try
            {
                files = Directory.GetFiles(current);
            }
            catch
            {
                continue;
            }

            foreach (var file in files)
            {
                yield return file;
            }
        }
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

            var toolName = ResolveToolName(step, step.Command ?? string.Empty, action);
            var lowerAction = action.ToLowerInvariant();
            if (toolName.Equals("calendar", StringComparison.OrdinalIgnoreCase))
            {
                var icsFiles = Directory.GetFiles(Path.GetTempPath(), "JarvisEvent_*.ics", SearchOption.TopDirectoryOnly);
                var latest = icsFiles.Length > 0 ? icsFiles[0] : string.Empty;
                evidence.Add(string.IsNullOrWhiteSpace(latest)
                    ? $"No calendar ICS artifact found for: {action}"
                    : $"Verified calendar ICS artifact exists: {latest}");
            }
            else if (IsFileCreation(action, out var pathCandidate))
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
            else if (lowerAction.Contains("explorer") || lowerAction.Contains("launch") || lowerAction.Contains("open"))
            {
                evidence.Add($"Verification requires an external process check for: {action}");
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

        if (IsCalendarEventAction(lower))
        {
            return ($"CALENDAR_EVENT:{normalized}", "Create a Windows calendar event for the requested date and message");
        }

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

    private static bool IsCalendarEventAction(string lowerStep)
    {
        return lowerStep.Contains("calendar")
            || lowerStep.Contains("meeting")
            || lowerStep.Contains("appointment")
            || lowerStep.Contains("reminder")
            || lowerStep.Contains("schedule")
            || lowerStep.Contains("event");
    }

    private static string ResolveToolName(TaskStep step, string command, string action)
    {
        if (!string.IsNullOrWhiteSpace(step?.Command))
        {
            return InferToolFromCommand(step.Command);
        }

        if (!string.IsNullOrWhiteSpace(step?.ToolId))
        {
            return NormalizeToolName(step.ToolId);
        }

        if (!string.IsNullOrWhiteSpace(step?.CapabilityId))
        {
            return NormalizeToolName(step.CapabilityId);
        }

        if (!string.IsNullOrWhiteSpace(command))
        {
            return InferToolFromCommand(command);
        }

        if (!string.IsNullOrWhiteSpace(action))
        {
            return InferToolFromCommand(action);
        }

        return "powershell";
    }

    private static string NormalizeToolName(string toolName)
    {
        if (string.IsNullOrWhiteSpace(toolName))
        {
            return "powershell";
        }

        var normalized = toolName.Trim().ToLowerInvariant();
        if (normalized.Contains("calendar"))
        {
            return "calendar";
        }
        if (normalized.Contains("flutter"))
        {
            return "flutter";
        }
        if (normalized.Contains("git"))
        {
            return "git";
        }
        if (normalized.Contains("cmd"))
        {
            return "cmd";
        }
        return "powershell";
    }

    private static string InferToolFromCommand(string command)
    {
        if (string.IsNullOrWhiteSpace(command))
        {
            return "powershell";
        }

        var trimmed = command.Trim();
        var lower = trimmed.ToLowerInvariant();
        if (trimmed.StartsWith("CALENDAR_EVENT:", StringComparison.OrdinalIgnoreCase))
        {
            return "calendar";
        }
        if (lower.StartsWith("flutter"))
        {
            return "flutter";
        }
        if (lower.StartsWith("git"))
        {
            return "git";
        }
        if (lower.StartsWith("cmd"))
        {
            return "cmd";
        }
        return "powershell";
    }

    private async Task<(bool success, string output, int exitCode)> ExecuteCalendarEventAsync(string command, string action)
    {
        try
        {
            var payload = command.StartsWith("CALENDAR_EVENT:", StringComparison.OrdinalIgnoreCase)
                ? command.Substring("CALENDAR_EVENT:".Length)
                : action;
            var (eventDate, eventMessage) = ParseCalendarEvent(payload);
            if (eventDate == null)
            {
                if (ShouldOpenCalendarApp(payload))
                {
                    return await OpenCalendarAppAsync();
                }

                return (false, "Unable to extract date and message for calendar event.", -1);
            }

            if (string.IsNullOrWhiteSpace(eventMessage))
            {
                eventMessage = "Calendar event";
            }

            var icsPath = CreateCalendarEventIcs(eventDate.Value, eventMessage);
            var processInfo = new ProcessStartInfo
            {
                FileName = icsPath,
                UseShellExecute = true,
            };

            using var process = Process.Start(processInfo);
            if (process == null)
            {
                return (false, $"Unable to launch the Windows Calendar experience for: {icsPath}", -1);
            }

            return (File.Exists(icsPath), $"Windows calendar event file created and opened: {icsPath}", 0);
        }
        catch (Exception ex)
        {
            return (false, ex.Message, -1);
        }
    }

    private static bool ShouldOpenCalendarApp(string action)
    {
        if (string.IsNullOrWhiteSpace(action))
        {
            return false;
        }

        var lower = action.ToLowerInvariant();
        return lower.Contains("calendar") && (lower.Contains("open") || lower.Contains("launch") || lower.Contains("start") || lower.Contains("app"));
    }

    private static async Task<(bool success, string output, int exitCode)> OpenCalendarAppAsync()
    {
        try
        {
            var processInfo = new ProcessStartInfo
            {
                FileName = "explorer.exe",
                Arguments = "shell:Appsfolder\\microsoft.windowscommunicationsapps_8wekyb3d8bbwe!microsoft.windowslive.calendar",
                UseShellExecute = true,
            };

            using var process = Process.Start(processInfo);
            if (process == null)
            {
                return (false, "Unable to open the Windows Calendar app.", -1);
            }

            return (true, "Windows Calendar app opened.", 0);
        }
        catch (Exception ex)
        {
            return (false, ex.Message, -1);
        }
    }

    private static (DateTime? date, string message) ParseCalendarEvent(string action)
    {
        var date = ExtractDate(action);
        var message = ExtractCalendarMessage(action);
        return (date, message);
    }

    private static DateTime? ExtractDate(string action)
    {
        if (string.IsNullOrWhiteSpace(action))
        {
            return null;
        }

        var normalized = action.Trim();

        // Try explicit date and time combinations such as "6/27/2026 3:00 PM", "2026-06-27 at 15:00", or "2026-06-27 3 PM".
        var dateTimePattern = new Regex(@"(?<datetime>\b(?:\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{1,2}-\d{1,2})(?:\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:[APap][Mm])?)?\b)", RegexOptions.IgnoreCase);
        var dateTimeMatch = dateTimePattern.Match(normalized);
        if (dateTimeMatch.Success)
        {
            if (DateTime.TryParse(dateTimeMatch.Groups["datetime"].Value, CultureInfo.InvariantCulture, DateTimeStyles.None, out var parsed))
            {
                return parsed;
            }
        }

        // Patterns like "on 6/27/2026" or "on June 27, 2026" with optional time.
        var onPattern = new Regex(@"\bon\s+(?<date>\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{1,2}-\d{1,2}|\w+ \d{1,2}(?:st|nd|rd|th)?(?:, \d{4})?)(?:\s+at\s+(?<time>\d{1,2}(?::\d{2})?(?:\s*[APap][Mm])?))?", RegexOptions.IgnoreCase);
        var onMatch = onPattern.Match(normalized);
        if (onMatch.Success)
        {
            var datePart = onMatch.Groups["date"].Value;
            var timePart = onMatch.Groups["time"].Success ? onMatch.Groups["time"].Value : string.Empty;
            var combined = string.IsNullOrWhiteSpace(timePart) ? datePart : $"{datePart} {timePart}";
            if (DateTime.TryParse(combined, CultureInfo.InvariantCulture, DateTimeStyles.None, out var parsed))
            {
                return parsed;
            }
        }

        var relativeTime = ExtractTime(normalized);
        if (Regex.IsMatch(normalized, "\btomorrow\b", RegexOptions.IgnoreCase))
        {
            var date = DateTime.Today.AddDays(1);
            return relativeTime.HasValue ? date.Add(relativeTime.Value) : date;
        }

        if (Regex.IsMatch(normalized, "\btoday\b", RegexOptions.IgnoreCase))
        {
            var date = DateTime.Today;
            return relativeTime.HasValue ? date.Add(relativeTime.Value) : date;
        }

        return null;
    }

    private static TimeSpan? ExtractTime(string action)
    {
        var timeMatch = Regex.Match(action, @"\b(?:at\s+)?(?<time>\d{1,2}(?::\d{2})?\s*(?:[APap][Mm]))\b", RegexOptions.IgnoreCase);
        if (!timeMatch.Success)
        {
            return null;
        }

        return DateTime.TryParse(timeMatch.Groups["time"].Value, CultureInfo.InvariantCulture, DateTimeStyles.NoCurrentDateDefault, out var parsed)
            ? parsed.TimeOfDay
            : null;
    }

    private static string ExtractCalendarMessage(string action)
    {
        if (string.IsNullOrWhiteSpace(action))
        {
            return string.Empty;
        }

        var splitByPipe = action.Split('|', 2);
        if (splitByPipe.Length > 1)
        {
            var titlePart = splitByPipe[0].Replace("CALENDAR_EVENT:", string.Empty, StringComparison.OrdinalIgnoreCase).Trim();
            var titleMatch = Regex.Match(titlePart, @"^(?<title>.+?)\s+at\s+(?:\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{1,2}-\d{1,2}|\w+ \d{1,2}(?:st|nd|rd|th)?(?:, \d{4})?)(?:\s+\d{1,2}(?::\d{2})?\s*(?:[APap][Mm])?)?$", RegexOptions.IgnoreCase);
            return (titleMatch.Success ? titleMatch.Groups["title"].Value : titlePart).Trim(' ', '"', '.');
        }

        var messagePattern = new Regex(@"(?:called|named|with description|with note|about)\s+(?<message>.+)$", RegexOptions.IgnoreCase);
        var match = messagePattern.Match(action);
        if (match.Success)
        {
            return match.Groups["message"].Value.Trim(' ', '"', '.');
        }

        var fallback = Regex.Replace(action, @".*?(?:add|create|schedule|set).*?(?:calendar|event|reminder)\s*", string.Empty, RegexOptions.IgnoreCase);
        var cleaned = fallback.Trim(' ', '"', '.');
        return string.IsNullOrWhiteSpace(cleaned) ? action.Trim(' ', '"', '.') : cleaned;
    }

    private static string CreateCalendarEventIcs(DateTime eventDate, string summary)
    {
        var uid = Guid.NewGuid().ToString();
        var start = eventDate.TimeOfDay == TimeSpan.Zero ? eventDate.Date.AddHours(9) : eventDate;
        var end = start.AddHours(1);
        var dtstamp = DateTime.UtcNow.ToString("yyyyMMddTHHmmssZ");
        var dtstart = start.ToString("yyyyMMddTHHmmss");
        var dtend = end.ToString("yyyyMMddTHHmmss");

        var ics = $"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nMETHOD:PUBLISH\r\nPRODID:-//Jarvis AI//EN\r\nBEGIN:VEVENT\r\nUID:{uid}\r\nDTSTAMP:{dtstamp}\r\nDTSTART:{dtstart}\r\nDTEND:{dtend}\r\nSUMMARY:{EscapeIcsText(summary)}\r\nDESCRIPTION:{EscapeIcsText(summary)}\r\nBEGIN:VALARM\r\nTRIGGER:-PT15M\r\nACTION:DISPLAY\r\nDESCRIPTION:Reminder\r\nEND:VALARM\r\nEND:VEVENT\r\nEND:VCALENDAR";

        var fileName = $"JarvisEvent_{uid}.ics";
        var filePath = Path.Combine(Path.GetTempPath(), fileName);
        File.WriteAllText(filePath, ics);
        return filePath;
    }

    private static string EscapeIcsText(string text)
    {
        return text.Replace("\\", "\\\\").Replace("\n", "\\n").Replace(",", "\\,").Replace(";", "\\;");
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

    private async Task<(bool success, string output, int exitCode)> RunPowerShellCommandAsync(string command)
    {
        return await RunProcessAsync("powershell", $"-NoProfile -NonInteractive -Command \"{command}\"");
    }

    private async Task<(bool success, string output, int exitCode)> RunFlutterCommandAsync(string command)
    {
        return await RunProcessAsync("flutter", command);
    }

    private async Task<(bool success, string output, int exitCode)> RunGitCommandAsync(string command)
    {
        return await RunProcessAsync("git", command);
    }

    private async Task<(bool success, string output, int exitCode)> RunCmdCommandAsync(string command)
    {
        return await RunProcessAsync("cmd.exe", $"/c {command}");
    }

    private static Task<(bool success, string output, int exitCode)> RunProcessAsync(string fileName, string arguments)
    {
        return Task.Run(() =>
        {
            var startInfo = new ProcessStartInfo
            {
                FileName = fileName,
                Arguments = arguments,
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
            return (process.ExitCode == 0, string.IsNullOrWhiteSpace(combined) ? "Command completed" : combined, process.ExitCode);
        });
    }
}
