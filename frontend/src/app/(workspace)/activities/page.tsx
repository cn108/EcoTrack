import { ActivityManager } from "@/components/activity-manager";

export default async function ActivitiesPage({
  searchParams,
}: {
  searchParams: Promise<{ new?: string | string[] }>;
}) {
  const params = await searchParams;
  return <ActivityManager initialOpen={params.new === "1"} />;
}