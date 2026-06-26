import { useMemo } from "react";
import { cn } from "../lib/utils";

interface CalendarEvent {
  id: string;
  title: string;
  start_time: number;
  end_time: number;
  status: string;
}

interface MonthCalendarProps {
  year: number;
  month: number; // 0-indexed
  events: CalendarEvent[];
  selectedDay: number | null;
  onSelectDay: (day: number) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
}

export default function MonthCalendar({
  year,
  month,
  events,
  selectedDay,
  onSelectDay,
  onPrevMonth,
  onNextMonth,
}: MonthCalendarProps) {
  const weeks = useMemo(() => {
    const first = new Date(year, month, 1);
    const last = new Date(year, month + 1, 0);
    const startPad = first.getDay(); // 0=Sun
    const daysInMonth = last.getDate();
    const cells: (number | null)[] = [];
    for (let i = 0; i < startPad; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);

    const w: (number | null)[][] = [];
    for (let i = 0; i < cells.length; i += 7) {
      w.push(cells.slice(i, i + 7));
    }
    return w;
  }, [year, month]);

  const eventsByDay = useMemo(() => {
    const map = new Map<number, CalendarEvent[]>();
    for (const ev of events) {
      if (!ev.start_time) continue;
      const d = new Date(ev.start_time / 1000);
      if (d.getFullYear() === year && d.getMonth() === month) {
        const day = d.getDate();
        const list = map.get(day) || [];
        list.push(ev);
        map.set(day, list);
      }
    }
    return map;
  }, [events, year, month]);

  const today = new Date();

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={onPrevMonth}
          className="text-sm text-muted-foreground hover:text-foreground px-2 py-1 rounded hover:bg-muted transition-colors"
        >
          ← {month === 0 ? monthNames[11] : monthNames[month - 1]}
        </button>
        <h3 className="text-base font-semibold">
          {monthNames[month]} {year}
        </h3>
        <button
          onClick={onNextMonth}
          className="text-sm text-muted-foreground hover:text-foreground px-2 py-1 rounded hover:bg-muted transition-colors"
        >
          {month === 11 ? monthNames[0] : monthNames[month + 1]} →
        </button>
      </div>

      {/* Day-of-week headers */}
      <div className="grid grid-cols-7 mb-1">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <div key={d} className="text-center text-[10px] text-muted-foreground font-medium py-1">
            {d}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="space-y-[1px]">
        {weeks.map((week, wi) => (
          <div key={wi} className="grid grid-cols-7 gap-[1px]">
            {week.map((day, di) => {
              if (day === null) {
                return <div key={`e-${wi}-${di}`} className="aspect-square" />;
              }
              const dayEvents = eventsByDay.get(day) || [];
              const isToday =
                today.getFullYear() === year &&
                today.getMonth() === month &&
                today.getDate() === day;
              const isSelected = selectedDay === day;

              return (
                <button
                  key={day}
                  onClick={() => onSelectDay(day)}
                  className={cn(
                    "aspect-square rounded-md text-xs flex flex-col items-center justify-center gap-[2px] transition-colors relative",
                    isSelected
                      ? "bg-primary/20 border border-primary/50"
                      : isToday
                      ? "bg-muted/50 border border-border/50"
                      : "hover:bg-muted/30 border border-transparent"
                  )}
                >
                  <span
                    className={cn(
                      "font-medium",
                      isToday && !isSelected ? "text-primary" : "text-foreground"
                    )}
                  >
                    {day}
                  </span>
                  {dayEvents.length > 0 && (
                    <div className="flex gap-[2px]">
                      {dayEvents.slice(0, 3).map((ev) => (
                        <div
                          key={ev.id}
                          className={cn(
                            "w-1.5 h-1.5 rounded-full",
                            ev.status === "completed"
                              ? "bg-success"
                              : ev.status === "cancelled"
                              ? "bg-destructive"
                              : ev.status === "confirmed"
                              ? "bg-primary"
                              : "bg-muted-foreground/50"
                          )}
                        />
                      ))}
                      {dayEvents.length > 3 && (
                        <span className="text-[8px] text-muted-foreground">
                          +{dayEvents.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
