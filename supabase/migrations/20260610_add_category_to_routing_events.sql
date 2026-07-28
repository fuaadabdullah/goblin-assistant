-- Add conversation category to routing_events for analytics
ALTER TABLE public.routing_events
  ADD COLUMN IF NOT EXISTS category TEXT;

CREATE INDEX IF NOT EXISTS routing_events_category_idx
  ON public.routing_events (category)
  WHERE category IS NOT NULL;
