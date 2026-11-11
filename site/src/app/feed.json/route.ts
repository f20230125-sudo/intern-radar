import { jsonFeed } from "@/lib/feed";
import { SITE_URL } from "@/lib/site";
import { loadSnapshot } from "@/lib/snapshot";

export const dynamic = "force-dynamic";

export async function GET() {
  const { snapshot } = await loadSnapshot();
  return Response.json(jsonFeed(snapshot, SITE_URL), {
    headers: { "Content-Type": "application/feed+json; charset=utf-8", "Cache-Control": "public, max-age=0, s-maxage=300, stale-while-revalidate=300" },
  });
}
