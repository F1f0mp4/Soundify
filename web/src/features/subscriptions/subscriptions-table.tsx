import { Panel } from "@/components/common/panel";
import { SourceIcon } from "@/components/icons/source-icon";
import type { Subscription } from "@/api/subscriptions";
import { useTimeAgo } from "@/hooks/use-time-ago";
import { Button, EmptyState, Spinner, Switch, Table } from "@heroui/react";
import {
  InboxIcon,
  ListMusicIcon,
  RefreshCwIcon,
  Trash2Icon,
  XIcon,
} from "lucide-react";
import { useCallback } from "react";

type ColumnKey = "name" | "lastSynced" | "limit" | "enabled" | "actions";

function TimeAgo({ dateString }: { dateString: string | null | undefined }) {
  return useTimeAgo(dateString);
}

const columns: { name: string; id: ColumnKey }[] = [
  { name: "Playlist", id: "name" },
  { name: "Last synced", id: "lastSynced" },
  { name: "Limit", id: "limit" },
  { name: "Enabled", id: "enabled" },
  { name: "Actions", id: "actions" },
];

type SubscriptionsTableProps = {
  subscriptions: Subscription[];
  isLoading?: boolean;
  isSchedulerEnabled?: boolean;
  onToggleEnabled: (id: string, enabled: boolean) => void;
  onRemoveLimit: (id: string) => void;
  onSync: (id: string) => void;
  onDelete: (id: string) => void;
};

export function SubscriptionsTable({
  subscriptions,
  isLoading,
  isSchedulerEnabled,
  onToggleEnabled,
  onRemoveLimit,
  onSync,
  onDelete,
}: SubscriptionsTableProps) {
  const renderCell = useCallback(
    (
      subscription: Subscription,
      isSchedulerEnabled: boolean,
      columnKey: ColumnKey,
    ) => {
      switch (columnKey) {
        case "name":
          return (
            <div className="flex items-center gap-3">
              <div className="relative shrink-0 max-md:hidden">
                {subscription.thumbnail_url ? (
                  <img
                    alt=""
                    src={subscription.thumbnail_url}
                    className="size-10 rounded-md object-cover"
                  />
                ) : (
                  <div className="bg-surface-tertiary flex size-10 items-center justify-center rounded-md">
                    <ListMusicIcon className="text-muted size-5" />
                  </div>
                )}
                <SourceIcon
                  source={subscription.source}
                  className="ring-background absolute -right-1.5 -bottom-1.5 size-[18px] ring-2"
                />
              </div>
              {/* Covers are hidden on small screens; keep the source visible. */}
              <SourceIcon source={subscription.source} className="md:hidden" />
              {subscription.name}
            </div>
          );
        case "lastSynced":
          return <TimeAgo dateString={subscription.last_synced_at} />;
        case "limit":
          if (subscription.max_items == null) {
            return <span className="text-muted">All</span>;
          }
          return (
            <div className="flex items-center gap-1">
              <span className="tnum">{subscription.max_items}</span>
              <Button
                variant="ghost"
                size="sm"
                isIconOnly
                aria-label="Remove track limit"
                className="icon-action size-6 min-w-6"
                onPress={() => onRemoveLimit(subscription.id)}
              >
                <XIcon className="size-3.5" />
              </Button>
            </div>
          );
        case "enabled":
          return (
            <Switch
              size="sm"
              isDisabled={!isSchedulerEnabled}
              isSelected={subscription.enabled}
              onChange={(enabled) => onToggleEnabled(subscription.id, enabled)}
              aria-label="Toggle auto-sync"
            >
              <Switch.Content>
                <Switch.Control>
                  <Switch.Thumb />
                </Switch.Control>
              </Switch.Content>
            </Switch>
          );
        case "actions":
          return (
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                isIconOnly
                aria-label="Sync now"
                className="icon-action"
                onPress={() => onSync(subscription.id)}
              >
                <RefreshCwIcon className="size-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                isIconOnly
                aria-label="Delete playlist"
                className="icon-action hover:text-danger"
                onPress={() => onDelete(subscription.id)}
              >
                <Trash2Icon className="size-4" />
              </Button>
            </div>
          );
      }
    },
    [onToggleEnabled, onRemoveLimit, onSync, onDelete],
  );

  return (
    // The table carries its own opaque surface; the panel supplies the frosted
    // one, so the table chrome is cleared out to let it show through.
    <Panel>
      <Table className="border-0 bg-transparent">
        <Table.ScrollContainer className="bg-transparent">
          <Table.Content
            aria-label="Subscribed playlists"
            className="bg-transparent"
          >
            <Table.Header columns={columns}>
              {(column) => (
                <Table.Column
                  id={column.id}
                  isRowHeader={column.id === "name"}
                  className="eyebrow bg-transparent font-normal"
                >
                  {column.name}
                </Table.Column>
              )}
            </Table.Header>
            <Table.Body
              items={isLoading ? [] : subscriptions}
              renderEmptyState={() =>
                isLoading ? (
                  <EmptyState className="flex min-h-[160px] w-full flex-col items-center justify-center gap-4 text-center">
                    <Spinner size="sm" />
                    <span className="text-muted text-sm">Loading...</span>
                  </EmptyState>
                ) : (
                  <EmptyState className="flex min-h-[160px] w-full flex-col items-center justify-center gap-4 text-center">
                    <InboxIcon className="text-muted size-6" />
                    <span className="text-muted text-sm">
                      No playlists registered
                    </span>
                  </EmptyState>
                )
              }
            >
              {(subscription) => (
                <Table.Row id={subscription.id} className="bg-transparent">
                  {columns.map((column) => (
                    <Table.Cell key={column.id} className="text-sm font-light">
                      {renderCell(
                        subscription,
                        !!isSchedulerEnabled,
                        column.id,
                      )}
                    </Table.Cell>
                  ))}
                </Table.Row>
              )}
            </Table.Body>
          </Table.Content>
        </Table.ScrollContainer>
      </Table>
    </Panel>
  );
}
