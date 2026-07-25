import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../../lib/query-client";
import { api } from "../../lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Select } from "../../components/ui/select";
import { Loader2, Sun, Moon, Palette } from "lucide-react";
import { toast } from "sonner";
import { useTheme } from "../../lib/theme";

const TICKET_STATUSES = ["new", "open", "in_progress", "resolved", "closed"];

export default function UserPreferencesSection() {
  const { theme, toggleTheme } = useTheme();
  const [form, setForm] = useState({
    theme: "dark",
    default_ticket_status: "new",
  });
  const [dirty, setDirty] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["user-settings"],
    queryFn: async () => {
      const res = await api.userSettings.get();
      if (res.settings) {
        setForm({
          theme: res.settings.theme,
          default_ticket_status: res.settings.default_ticket_status,
        });
      }
      return res;
    },
  });

  const saveMutation = useMutation({
    mutationFn: (data: { theme: string; default_ticket_status: string }) =>
      api.userSettings.update(data),
    onSuccess: () => {
      toast.success("Preferences saved");
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["user-settings"] });
    },
    onError: () => {
      toast.error("Failed to save preferences");
    },
  });

  const handleThemeChange = (newTheme: "light" | "dark") => {
    setForm({ ...form, theme: newTheme });
    setDirty(true);
    // Sync the app theme hook immediately for instant feedback
    if (newTheme !== theme) {
      toggleTheme();
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Palette className="h-4 w-4" />
          User Preferences
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Customize your personal workspace theme and default ticket status.
        </p>

        {/* Theme selector */}
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">Theme</label>
          <div className="flex gap-1 rounded-lg border border-border p-1">
            <button
              type="button"
              onClick={() => handleThemeChange("light")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                form.theme === "light"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Sun className="h-3.5 w-3.5" />
              Light
            </button>
            <button
              type="button"
              onClick={() => handleThemeChange("dark")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                form.theme === "dark"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Moon className="h-3.5 w-3.5" />
              Dark
            </button>
          </div>
        </div>

        {/* Default ticket status */}
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">Default Ticket Status</label>
          <Select
            value={form.default_ticket_status}
            onChange={(e) => {
              setForm({ ...form, default_ticket_status: e.target.value });
              setDirty(true);
            }}
            className="w-40"
          >
            {TICKET_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex justify-end border-t pt-3">
          <Button
            onClick={() => saveMutation.mutate(form)}
            disabled={!dirty || saveMutation.isPending}
          >
            {saveMutation.isPending ? (
              <>
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                Saving...
              </>
            ) : (
              "Save Preferences"
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
