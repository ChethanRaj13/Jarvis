namespace windowsAssistant.UI.Services;

public class PlanningService
{
    public List<string> GeneratePlan(string command)
    {
        command = command.ToLower();

        // INSTALL / SETUP
        if (command.Contains("install") || command.Contains("setup"))
        {
            return new List<string>
            {
                "Analyze Installation Requirements",
                "Download Required Files",
                "Install Application",
                "Configure Environment",
                "Verify Installation"
            };
        }

        // DELETE
        if (command.Contains("delete") || command.Contains("remove"))
        {
            return new List<string>
            {
                "Locate Target",
                "Check Permissions",
                "Delete Resource",
                "Verify Deletion"
            };
        }

        // COPY
        if (command.Contains("copy"))
        {
            return new List<string>
            {
                "Locate Source",
                "Locate Destination",
                "Copy Files",
                "Verify Copy"
            };
        }

        // MOVE
        if (command.Contains("move"))
        {
            return new List<string>
            {
                "Locate Source",
                "Locate Destination",
                "Move Resource",
                "Verify Move"
            };
        }

        // CREATE
        if (command.Contains("create"))
        {
            return new List<string>
            {
                "Analyze Request",
                "Create Resource",
                "Apply Configuration",
                "Verify Creation"
            };
        }

        // OPEN
        if (command.Contains("open"))
        {
            return new List<string>
            {
                "Locate Application",
                "Launch Application",
                "Verify Launch"
            };
        }

        // DOWNLOAD
        if (command.Contains("download"))
        {
            return new List<string>
            {
                "Locate Download Source",
                "Download Files",
                "Validate Download",
                "Save Files"
            };
        }

        // SHUTDOWN
        if (command.Contains("shutdown"))
        {
            return new List<string>
            {
                "Check Running Applications",
                "Save Pending Work",
                "Shutdown System"
            };
        }

        // RESTART
        if (command.Contains("restart"))
        {
            return new List<string>
            {
                "Close Running Applications",
                "Restart System",
                "Verify Startup"
            };
        }

        // DEFAULT
        return new List<string>
        {
            "Analyze User Request",
            "Generate Execution Plan",
            "Execute Task",
            "Verify Result"
        };
    }
}