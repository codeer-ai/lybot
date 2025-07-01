import React from 'react';
import { CheckCircle2, Settings, Loader2 } from 'lucide-react';
import type { ToolCall } from '@/lib/types';

interface ToolCallDisplayProps {
  toolCalls: ToolCall[];
  isComplete: boolean;
}

const ToolCallDisplay: React.FC<ToolCallDisplayProps> = ({ toolCalls, isComplete }) => {
  if (!toolCalls || toolCalls.length === 0) {
    return null;
  }

  return (
    <div className="mb-4 p-4 bg-muted/30 border border-border/40 rounded-xl space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        {isComplete ? (
          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
        ) : (
          <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
        )}
        <span>查詢過程</span>
        {!isComplete && <span className="text-xs text-blue-500">處理中...</span>}
      </div>
      
      <div className="space-y-2">
        {toolCalls.map((toolCall, index) => {
          const args = JSON.parse(toolCall.function.arguments);
          
          return (
            <div key={toolCall.id || index} className="flex items-start gap-3 p-3 bg-background/50 rounded-lg border border-border/30">
              <Settings className="w-4 h-4 mt-0.5 text-violet-500 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm text-foreground mb-1">
                  {getToolDisplayName(toolCall.function.name)}
                </div>
                <div className="text-xs space-y-1">
                  {Object.entries(args).map(([key, value]) => (
                    <div key={key} className="flex gap-2">
                      <span className="text-muted-foreground font-medium min-w-0 flex-shrink-0">
                        {getParamDisplayName(key)}:
                      </span>
                      <span className="text-foreground/80 break-words">
                        {formatParamValue(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              {isComplete && (
                <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
              )}
            </div>
          );
        })}
      </div>
      
      {isComplete && (
        <div className="flex items-center gap-2 pt-2 border-t border-border/30">
          <div className="h-1 w-1 bg-emerald-500 rounded-full"></div>
          <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
            查詢完成，正在生成回應...
          </span>
        </div>
      )}
    </div>
  );
};

// Helper functions to make tool names and parameters more user-friendly
function getToolDisplayName(toolName: string): string {
  const displayNames: Record<string, string> = {
    'get_party_seat_count': '查詢政黨席次統計',
    'get_legislator_by_constituency': '查詢選區立委',
    'get_legislator_details': '查詢立委詳細資訊',
    'search_bills': '搜尋法案',
    'get_bill_details': '查詢法案詳情',
    'search_interpellations': '搜尋質詢記錄',
    'calculate_attendance_rate': '計算出席率',
    'analyze_party_statistics': '分析政黨統計',
    // Add more mappings as needed
  };
  
  return displayNames[toolName] || toolName;
}

function getParamDisplayName(paramName: string): string {
  const displayNames: Record<string, string> = {
    'party': '政黨',
    'term': '屆期',
    'constituency': '選區',
    'name': '姓名',
    'keyword': '關鍵字',
    'limit': '數量限制',
    'session': '會期',
    'bill_id': '法案編號',
    // Add more mappings as needed
  };
  
  return displayNames[paramName] || paramName;
}

function formatParamValue(value: any): string {
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number') {
    return value.toString();
  }
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  return JSON.stringify(value);
}

export default ToolCallDisplay;