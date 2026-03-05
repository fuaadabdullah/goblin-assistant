import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, Badge } from '../../components/ui';
import { DollarSign, TrendingUp, TrendingDown } from 'lucide-react';
import { formatCurrency } from '../../lib/utils';

interface CostOverviewBannerProps {
  totalCost: number;
  todayCost: number;
  thisMonthCost: number;
  byProvider: Record<string, number>;
}

export function CostOverviewBanner({ totalCost, todayCost, thisMonthCost, byProvider }: CostOverviewBannerProps) {
  return (
    <Card className="border-green-200">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-100 rounded-full">
              <DollarSign className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <CardTitle className="text-green-900">Cost Overview</CardTitle>
              <p className="text-sm text-green-600">Real-time spending insights</p>
            </div>
          </div>
          <div className="flex space-x-2">
            <Badge variant="default">Today: {formatCurrency(todayCost)}</Badge>
            <Badge variant="secondary">This Month: {formatCurrency(thisMonthCost)}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-green-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-green-600">Total Cost</p>
                <p className="text-2xl font-bold text-green-900">{formatCurrency(totalCost)}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-500" />
            </div>
          </div>
          
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-600">Today's Cost</p>
                <p className="text-2xl font-bold text-blue-900">{formatCurrency(todayCost)}</p>
              </div>
              <TrendingDown className="h-8 w-8 text-blue-500" />
            </div>
          </div>
          
          <div className="bg-purple-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-purple-600">This Month</p>
                <p className="text-2xl font-bold text-purple-900">{formatCurrency(thisMonthCost)}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-purple-500" />
            </div>
          </div>
        </div>
        
        {Object.keys(byProvider).length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <h4 className="text-sm font-medium text-gray-700 mb-2">By Provider</h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(byProvider).map(([provider, cost]) => (
                <Badge key={provider} variant="outline" className="text-sm">
                  {provider}: {formatCurrency(cost)}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
