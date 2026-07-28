import type { Meta, StoryObj } from '@storybook/react';
import {
  Bell,
  BrainCircuit,
  Check,
  Command,
  Home,
  LayoutDashboard,
  Settings,
  Sparkles,
} from 'lucide-react';
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarItem,
  SidebarSeparator,
  Skeleton,
  Spinner,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Tooltip,
} from '@goblin/ui';

const tokenSwatches = [
  ['Background', 'var(--bg)'],
  ['Surface', 'var(--surface)'],
  ['Primary', 'var(--primary)'],
  ['Accent', 'var(--accent)'],
  ['Success', 'var(--success)'],
  ['Warning', 'var(--warning)'],
  ['Danger', 'var(--danger)'],
  ['Info', 'var(--info)'],
] as const;

const meta = {
  title: 'Design System/Foundation',
  parameters: {
    layout: 'fullscreen',
  },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const WorkspaceCore: Story = {
  render: () => (
    <div className="min-h-screen bg-bg p-6 text-text">
      <div className="mx-auto flex max-w-7xl gap-6">
        <Sidebar className="hidden min-h-[720px] w-64 lg:flex">
          <SidebarHeader>
            <div className="flex items-center gap-3">
              <Avatar name="Goblin Assistant" size="sm" />
              <div>
                <p className="mb-0 text-sm font-semibold text-text-primary">GoblinOS</p>
                <p className="mb-0 text-xs text-text-muted">Workspace Core</p>
              </div>
            </div>
          </SidebarHeader>
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupLabel>Workspace</SidebarGroupLabel>
              <SidebarItem active icon={<LayoutDashboard className="h-4 w-4" />}>
                Overview
              </SidebarItem>
              <SidebarItem icon={<BrainCircuit className="h-4 w-4" />}>Agents</SidebarItem>
              <SidebarItem icon={<Command className="h-4 w-4" />}>Commands</SidebarItem>
            </SidebarGroup>
            <SidebarSeparator />
            <SidebarGroup>
              <SidebarGroupLabel>System</SidebarGroupLabel>
              <SidebarItem icon={<Bell className="h-4 w-4" />}>Signals</SidebarItem>
              <SidebarItem icon={<Settings className="h-4 w-4" />}>Settings</SidebarItem>
            </SidebarGroup>
          </SidebarContent>
        </Sidebar>

        <main className="grid flex-1 gap-6">
          <section className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <CardTitle>Component Library 2.0</CardTitle>
                    <CardDescription>
                      Token-backed primitives for the unified workspace shell.
                    </CardDescription>
                  </div>
                  <Badge variant="success" icon={<Check className="h-3 w-3" />}>
                    AA tokens
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {tokenSwatches.map(([label, value]) => (
                    <div key={label} className="rounded-md border border-border bg-surface p-3">
                      <div
                        className="mb-3 h-12 rounded-sm border border-border"
                        style={{ background: value }}
                      />
                      <p className="mb-0 text-xs font-semibold text-text-primary">{label}</p>
                      <p className="mb-0 text-xs text-text-muted">{value}</p>
                    </div>
                  ))}
                </div>

                <Tabs defaultValue="controls">
                  <TabsList aria-label="Foundation areas">
                    <TabsTrigger value="controls">Controls</TabsTrigger>
                    <TabsTrigger value="feedback">Feedback</TabsTrigger>
                    <TabsTrigger value="navigation">Navigation</TabsTrigger>
                  </TabsList>
                  <TabsContent value="controls" className="space-y-4 pt-4">
                    <div className="grid gap-4 md:grid-cols-2">
                      <Input aria-label="Workspace name" placeholder="Workspace name" />
                      <Select defaultValue="balanced">
                        <SelectTrigger aria-label="Agent mode">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="fast">Fast</SelectItem>
                          <SelectItem value="balanced">Balanced</SelectItem>
                          <SelectItem value="deep">Deep</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <Button icon={<Sparkles className="h-4 w-4" />}>Start Run</Button>
                      <Button variant="secondary">Queue</Button>
                      <Button variant="ghost">Cancel</Button>
                      <Button variant="danger">Stop</Button>
                    </div>
                  </TabsContent>
                  <TabsContent value="feedback" className="space-y-4 pt-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <Spinner />
                      <Skeleton className="h-5 w-40" />
                      <Skeleton tone="subtle" className="h-5 w-28" />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge>Default</Badge>
                      <Badge variant="info">Info</Badge>
                      <Badge variant="warning">Warning</Badge>
                      <Badge variant="danger">Danger</Badge>
                    </div>
                  </TabsContent>
                  <TabsContent value="navigation" className="space-y-4 pt-4">
                    <div className="flex flex-wrap gap-3">
                      <Tooltip content="Pinned workspace">
                        <Button variant="secondary" icon={<Home className="h-4 w-4" />}>
                          Home
                        </Button>
                      </Tooltip>
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button variant="secondary">Open Dialog</Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>Confirm Workspace Action</DialogTitle>
                            <DialogDescription>
                              Dialog primitives share focus, overlay, motion, and radius tokens.
                            </DialogDescription>
                          </DialogHeader>
                        </DialogContent>
                      </Dialog>
                      <Sheet>
                        <SheetTrigger asChild>
                          <Button variant="secondary">Open Sheet</Button>
                        </SheetTrigger>
                        <SheetContent>
                          <SheetHeader>
                            <SheetTitle>Workspace Inspector</SheetTitle>
                            <SheetDescription>
                              Sheet primitives use the same Radix foundation as dialogs.
                            </SheetDescription>
                          </SheetHeader>
                        </SheetContent>
                      </Sheet>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Typography Scale</CardTitle>
                <CardDescription>Display, heading, body, and metadata tokens.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase text-text-muted">Display</p>
                  <p className="mb-0 text-4xl font-semibold text-text-primary">Quiet Control</p>
                </div>
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase text-text-muted">Heading</p>
                  <p className="mb-0 text-xl font-semibold text-text-primary">Agent Workspace</p>
                </div>
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase text-text-muted">Body</p>
                  <p className="mb-0 text-sm text-text-secondary">
                    Dense, readable interfaces built on an 8px spacing grid.
                  </p>
                </div>
              </CardContent>
            </Card>
          </section>
        </main>
      </div>
    </div>
  ),
};
