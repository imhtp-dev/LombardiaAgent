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
    <Card className="group relative overflow-hidden border border-gray-200/60 hover:border-gray-300 hover:shadow-xl transition-all duration-300 cursor-default backdrop-blur-sm bg-white">
      {/* Subtle gradient overlay on hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-gray-50/30 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
      
      <CardContent className="p-6 relative">
        <div className="flex items-center justify-between">
          <div className="space-y-3 flex-1">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              {title}
            </p>
            <h3 className="text-3xl font-bold tracking-tight text-gray-900 group-hover:scale-105 transform transition-transform duration-200">
              {value}
            </h3>
            {trend && (
              <p className={cn(
                "text-xs font-semibold flex items-center gap-1.5",
                trend.isPositive ? "text-green-600" : "text-red-600"
              )}>
                <span className="text-base">{trend.isPositive ? "↑" : "↓"}</span>
                <span>{Math.abs(trend.value)}%</span>
                <span className="text-gray-500 font-normal">vs last period</span>
              </p>
            )}
          </div>
          <div className={cn(
            "h-16 w-16 rounded-2xl flex items-center justify-center shadow-sm group-hover:shadow-md group-hover:scale-110 transform transition-all duration-300",
            iconColor === "text-blue-600" && "bg-gradient-to-br from-blue-50 to-blue-100/80",
            iconColor === "text-green-600" && "bg-gradient-to-br from-green-50 to-green-100/80",
            iconColor === "text-yellow-600" && "bg-gradient-to-br from-yellow-50 to-yellow-100/80",
            iconColor === "text-purple-600" && "bg-gradient-to-br from-purple-50 to-purple-100/80"
          )}>
            <Icon className={cn("h-8 w-8 group-hover:scale-110 transform transition-transform duration-300", iconColor)} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
