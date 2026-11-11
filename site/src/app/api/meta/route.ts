import { loadSnapshot } from "@/lib/snapshot";
import { openRoles } from "@/lib/stats";

// A few bytes the open page asks for now and then, to learn whether a newer check has landed.
export const dynamic = "force-dynamic";

export async function GET() {
  const { snapshot } = await loadSnapshot();
  return Response.json(
    { generated_at: snapshot.generated_at, open: openRoles(snapshot).length },
    { headers: { "Cache-Control": "public, max-age=0, s-maxage=60, stale-while-revalidate=60" } },
  );
}
