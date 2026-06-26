namespace windowsAssistant.UI.Services;

public class PlanningService
{
    public List<string> GeneratePlan(string command)
    {
        command = command.ToLower();

        if (command.Contains("flutter"))
        {
            return new List<string>
            {
                "Install Git",
                "Download Flutter SDK",
                "Configure PATH",
                "Run Flutter Doctor",
                "Verify Installation"
            };
        }

        if (command.Contains("react"))
        {
            return new List<string>
            {
                "Install Node.js",
                "Create React Project",
                "Install Dependencies",
                "Run React App",
                "Verify Setup"
            };
        }

        if (command.Contains("chrome"))
        {
            return new List<string>
            {
                "Locate Chrome",
                "Launch Browser",
                "Verify Browser Started"
            };
        }

        return new List<string>
        {
            "Analyze Request",
            "Create Execution Plan",
            "Execute Task",
            "Verify Result"
        };
    }
}