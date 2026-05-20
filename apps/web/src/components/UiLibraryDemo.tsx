import Button from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import Badge from '@/components/ui/Badge';

export function UiLibraryDemo() {
  return (
    <div className="p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>shadcn/ui Integration</CardTitle>
          <CardDescription>
            Successfully integrated shadcn/ui component library with Tailwind CSS
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button>Default Button</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="danger">Danger</Button>
          </div>

          <div className="space-y-2">
            <Input placeholder="shadcn/ui Input component" />
          </div>

          <div className="flex gap-2">
            <Badge>Default</Badge>
            <Badge variant="neutral">Neutral</Badge>
            <Badge variant="neutral">Subtle</Badge>
            <Badge variant="danger">Danger</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
