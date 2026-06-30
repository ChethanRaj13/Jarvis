using System;
using System.Configuration;
using System.Data;
using System.IO;
using System.Windows;

namespace windowsAssistant.UI;

/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        AppDomain.CurrentDomain.UnhandledException += CurrentDomain_UnhandledException;
        DispatcherUnhandledException += App_DispatcherUnhandledException;
        TaskScheduler.UnobservedTaskException += TaskScheduler_UnobservedTaskException;

        try
        {
            base.OnStartup(e);
        }
        catch (Exception ex)
        {
            LogUnhandledException(ex, "OnStartup");
            throw;
        }
    }

    private void App_DispatcherUnhandledException(object sender, System.Windows.Threading.DispatcherUnhandledExceptionEventArgs e)
    {
        LogUnhandledException(e.Exception, "DispatcherUnhandledException");
        e.Handled = false;
    }

    private void CurrentDomain_UnhandledException(object sender, UnhandledExceptionEventArgs e)
    {
        if (e.ExceptionObject is Exception ex)
        {
            LogUnhandledException(ex, "CurrentDomain_UnhandledException");
        }
        else
        {
            LogText($"Unhandled non-exception object: {e.ExceptionObject}", "CurrentDomain_UnhandledException");
        }
    }

    private void TaskScheduler_UnobservedTaskException(object? sender, UnobservedTaskExceptionEventArgs e)
    {
        LogUnhandledException(e.Exception, "TaskScheduler_UnobservedTaskException");
        e.SetObserved();
    }

    private static void LogUnhandledException(Exception exception, string source)
    {
        LogText($"[{DateTime.UtcNow:o}] {source}: {exception}", source);
    }

    private static void LogText(string text, string source)
    {
        try
        {
            var path = Path.Combine(Path.GetTempPath(), "JarvisUiCrashLog.txt");
            File.AppendAllText(path, text + Environment.NewLine + Environment.NewLine);
            Console.WriteLine(text);
        }
        catch
        {
            // Ignore failures during logging.
        }
    }
}

