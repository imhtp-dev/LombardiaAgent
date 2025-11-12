import { Card, CardContent } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  iconColor?: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
}

export function StatCard({ title, value, icon: Icon, iconColor = "text-blue-600", trend }: StatCardProps) {
  return (
    <Card className="overflow-hidden border-gray-200 hover:shadow-md transition-all duration-200">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2 flex-1">
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              {title}
            </p>
            <h3 className="text-3xl font-bold tracking-tight">
              {value}
            </h3>
            {trend && (
              <p className={cn(
                "text-xs font-medium flex items-center gap-1",
                trend.isPositive ? "text-green-600" : "text-red-600"
              )}>
                <span>{trend.isPositive ? "↑" : "↓"}</span>
                <span>{Math.abs(trend.value)}%</span>
                <span className="text-muted-foreground">vs last period</span>
              </p>
            )}
          </div>
          <div className={cn(
            "h-14 w-14 rounded-full flex items-center justify-center",
            iconColor === "text-blue-600" && "bg-blue-100",
            iconColor === "text-green-600" && "bg-green-100",
            iconColor === "text-yellow-600" && "bg-yellow-100",
            iconColor === "text-purple-600" && "bg-purple-100"
          )}>
            <Icon className={cn("h-7 w-7", iconColor)} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
