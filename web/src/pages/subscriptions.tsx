import { UrlInput } from "@/components/common/url-input";
import { SubscriptionsTable } from "@/features/subscriptions/subscriptions-table";
import { useSubscriptions } from "@/features/subscriptions/use-subscriptions";
import { useScheduleCountdown } from "@/hooks/use-schedule-countdown";
import { isValidUrl } from "@/lib/url";
import {
  Alert,
  Button,
  cn,
  InputGroup,
  NumberField,
  Spinner,
} from "@heroui/react";
import {
  CircleQuestionMarkIcon,
  HashIcon,
  RefreshCw,
  ZapIcon,
  ZapOffIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { useState } from "react";

const DEFAULT_MAX_ITEMS = 100;

function Stat({
  label,
  children,
  suffix,
  isDimmed,
}: {
  label: string;
  children: ReactNode;
  suffix?: string;
  isDimmed?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-2 px-6 py-6",
        isDimmed && "opacity-45",
      )}
    >
      <span className="tnum text-foreground text-2xl leading-none font-extralight">
        {children}
        {suffix && (
          <span className="text-muted ml-1.5 text-xs font-normal">
            {suffix}
          </span>
        )}
      </span>
      <span className="eyebrow">{label}</span>
    </div>
  );
}

export function SubscriptionsPage() {
  const [url, setUrl] = useState("");
  const [maxItems, setMaxItems] = useState(DEFAULT_MAX_ITEMS);
  const [isAdding, setIsAdding] = useState(false);
  const {
    subscriptions,
    schedulerStatus,
    isLoading,
    addSubscription,
    updateSubscription,
    deleteSubscription,
    syncSubscription,
    syncAll,
  } = useSubscriptions();
  const [isSyncing, setIsSyncing] = useState(false);

  const canAdd = isValidUrl(url);
  const isEmpty = subscriptions.length == 0;
  const canSyncAll = !isEmpty && !isSyncing && !isLoading;

  const handleAdd = async () => {
    if (!canAdd) return;
    setIsAdding(true);
    const success = await addSubscription(url.trim(), maxItems);
    if (success) {
      setUrl("");
    }
    setIsAdding(false);
  };

  const handleToggleEnabled = async (id: string, enabled: boolean) => {
    await updateSubscription(id, { enabled });
  };

  const handleSyncAll = async () => {
    setIsSyncing(true);
    await syncAll();
    setIsSyncing(false);
  };

  const countdown = useScheduleCountdown(
    schedulerStatus?.cron_expression,
    schedulerStatus?.timezone,
  );
  const enabledCount = subscriptions.filter((s) => s.enabled).length;
  const totalCount = subscriptions.length;
  const schedulerOff = schedulerStatus?.enabled === false;

  return (
    <>
      {/* Subscribe form */}
      <section className="glass mb-8 rounded-[1.75rem] p-2.5">
        <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center">
          <div className="min-w-0 flex-1">
            <UrlInput
              value={url}
              onChange={setUrl}
              disabled={isAdding}
              placeholder="Playlist link to keep in sync"
            />
          </div>

          <div className="flex items-center gap-2.5">
            <NumberField
              className="w-24 shrink-0"
              aria-label="Max tracks to sync per run"
              value={maxItems}
              onChange={(value) => {
                if (!Number.isNaN(value) && value >= 1) setMaxItems(value);
              }}
              minValue={1}
              maxValue={10000}
            >
              <InputGroup className="rounded-full border-0 bg-transparent">
                <InputGroup.Prefix>
                  <HashIcon
                    className="text-muted h-3.5 w-3.5"
                    strokeWidth={1.25}
                  />
                </InputGroup.Prefix>
                <InputGroup.Input
                  placeholder="Max"
                  className="tnum w-full min-w-0 bg-transparent"
                />
              </InputGroup>
            </NumberField>

            <Button
              variant="primary"
              className="h-11 shrink-0 rounded-full px-6 text-xs tracking-[0.16em] uppercase max-sm:flex-1"
              onPress={handleAdd}
              isDisabled={!canAdd}
              isPending={isAdding}
            >
              {({ isPending }) => (
                <>
                  {isPending ? (
                    <Spinner color="current" size="sm" />
                  ) : (
                    <ZapIcon className="h-4 w-4" strokeWidth={1.5} />
                  )}
                  Subscribe
                </>
              )}
            </Button>
          </div>
        </div>
      </section>

      {/* Scheduler summary */}
      <section className="glass mb-6 grid grid-cols-2 divide-x divide-[var(--separator)] rounded-[1.75rem] sm:grid-cols-3">
        <Stat
          label="Active"
          suffix={`of ${totalCount}`}
          isDimmed={schedulerOff}
        >
          {enabledCount}
        </Stat>
        <Stat label="Next sync" isDimmed={schedulerOff}>
          {countdown}
        </Stat>

        {/* Padding lives on the button so the whole cell is the hit target. */}
        <button
          type="button"
          disabled={!canSyncAll}
          onClick={handleSyncAll}
          className="group hover:bg-foreground/[0.04] col-span-2 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-b-[1.75rem] px-6 py-6 transition-colors disabled:cursor-not-allowed disabled:opacity-45 sm:col-span-1 sm:rounded-r-[1.75rem] sm:rounded-bl-none"
        >
          <RefreshCw
            size={20}
            strokeWidth={1.25}
            className={cn(
              isSyncing
                ? "text-accent animate-spin"
                : "transition-transform duration-500 group-hover:rotate-180",
            )}
          />
          <span className="eyebrow">
            {isSyncing ? "Syncing" : "Sync all now"}
          </span>
        </button>
      </section>

      {schedulerOff && (
        <div className="mb-6 flex w-full items-center justify-center">
          <Alert status="warning">
            <Alert.Indicator>
              <ZapOffIcon size={18} strokeWidth={1.25} />
            </Alert.Indicator>
            <Alert.Content>
              <Alert.Title>Scheduler is disabled.</Alert.Title>
              <Alert.Description>
                You can still add playlists and sync them manually.
              </Alert.Description>
            </Alert.Content>
            <a
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Configuration docs"
              href="https://github.com/guillevc/yubal?tab=readme-ov-file#%EF%B8%8F-configuration"
            >
              <CircleQuestionMarkIcon
                size={20}
                strokeWidth={1.25}
                className="mr-2"
              />
            </a>
          </Alert>
        </div>
      )}

      <SubscriptionsTable
        subscriptions={subscriptions}
        isLoading={isLoading}
        isSchedulerEnabled={schedulerStatus?.enabled}
        onToggleEnabled={handleToggleEnabled}
        onSync={syncSubscription}
        onDelete={deleteSubscription}
      />
    </>
  );
}
