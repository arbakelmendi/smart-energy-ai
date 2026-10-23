import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth";
import { adminSelectedId, deactivationWarning, statusActionAllowed } from "@/lib/admin-view";
import {
  useAdminUser,
  useAdminUsers,
  useAdminUserStatus,
  useAdminBuildings,
} from "@/hooks/use-admin";
import type { AdminUser, AdminUserFilters } from "@/lib/api/admin";
import { AdminState, AdminPagination, AdminBuildingsTable } from "@/components/admin-common";
function UserStatus({ target }: { target: AdminUser }) {
  const { user } = useAuth();
  const mutation = useAdminUserStatus();
  const [confirm, setConfirm] = useState(false);
  const allowed = !!user && statusActionAllowed(user.id, target.id, target.is_active);
  async function change() {
    try {
      await mutation.mutateAsync({ id: target.id, is_active: !target.is_active });
      setConfirm(false);
    } catch {
      /* Render safe server error. */
    }
  }
  return (
    <div className="space-y-3">
      <Button
        variant="wire"
        disabled={!allowed || mutation.isPending}
        onClick={() => {
          mutation.reset();
          if (target.is_active) setConfirm(true);
          else void change();
        }}
      >
        {target.is_active ? "Deactivate account" : "Activate account"}
      </Button>
      {!allowed ? (
        <p className="text-xs">Your own administrator account cannot be deactivated here.</p>
      ) : null}
      {confirm && target.is_active ? (
        <div
          role="alertdialog"
          aria-label="Confirm account deactivation"
          className="rounded-md border p-4"
        >
          <p>{deactivationWarning}</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <Button
              variant="destructive"
              disabled={mutation.isPending}
              onClick={() => {
                void change();
              }}
            >
              {mutation.isPending ? "Deactivating..." : "Confirm deactivation"}
            </Button>
            <Button
              variant="wire"
              disabled={mutation.isPending}
              onClick={() => {
                setConfirm(false);
                mutation.reset();
              }}
            >
              Cancel deactivation
            </Button>
          </div>
        </div>
      ) : null}
      {mutation.error ? (
        <p role="alert" className="text-destructive">
          {mutation.error.message}
        </p>
      ) : null}
    </div>
  );
}
function OwnedBuildings({ id }: { id: number }) {
  const [offset, setOffset] = useState(0);
  const query = useAdminBuildings({ owner_id: id, limit: 50, offset });
  return (
    <Panel title="Owned buildings">
      <AdminState
        pending={query.isPending}
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      >
        {query.data ? (
          <>
            <AdminBuildingsTable items={query.data.items} />
            <AdminPagination total={query.data.total} offset={offset} onChange={setOffset} />
          </>
        ) : null}
      </AdminState>
    </Panel>
  );
}
function UserDetail({ id }: { id: number }) {
  const query = useAdminUser(id);
  return (
    <div className="space-y-5">
      <Link to="/admin/users" search={{}} className="underline">
        Back to users
      </Link>
      <AdminState
        pending={query.isPending}
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      >
        {query.data ? (
          <Panel title={query.data.full_name}>
            <div className="space-y-3 break-words text-sm" data-admin-user-detail={query.data.id}>
              <p>{query.data.email}</p>
              <p>
                {query.data.role} | {query.data.is_active ? "Active" : "Inactive"}
              </p>
              <p>Created (UTC): {query.data.created_at.replace("T", " ")}</p>
              <p>Updated (UTC): {query.data.updated_at.replace("T", " ")}</p>
              <p>
                Buildings: {query.data.building_count} | Measurements:{" "}
                {query.data.measurement_count} | Predictions: {query.data.prediction_count}
              </p>
              <UserStatus target={query.data} />
              <p className="text-xs text-muted-foreground">
                Role assignment uses the existing administrator CLI. User deletion and password
                reset are unsupported.
              </p>
            </div>
          </Panel>
        ) : null}
      </AdminState>
      {query.data && !query.isError ? <OwnedBuildings id={id} /> : null}
    </div>
  );
}
function UsersList() {
  const [filters, setFilters] = useState<AdminUserFilters>({ limit: 50, offset: 0 });
  const query = useAdminUsers(filters);
  return (
    <Panel title="Accounts">
      <form
        className="mb-5 flex flex-wrap gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          const data = new FormData(e.currentTarget);
          const role = String(data.get("role"));
          const active = String(data.get("active"));
          setFilters({
            limit: 50,
            offset: 0,
            search: String(data.get("search")),
            ...(role ? { role: role as "USER" | "ADMIN" } : {}),
            ...(active ? { is_active: active === "true" } : {}),
          });
        }}
      >
        <Input
          name="search"
          aria-label="Search users"
          placeholder="Email or name"
          className="w-full sm:w-64"
        />
        <select
          name="role"
          aria-label="Filter role"
          className="rounded-md border bg-background p-2"
        >
          <option value="">All roles</option>
          <option>USER</option>
          <option>ADMIN</option>
        </select>
        <select
          name="active"
          aria-label="Filter status"
          className="rounded-md border bg-background p-2"
        >
          <option value="">All statuses</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
        <Button type="submit">Search users</Button>
      </form>
      <AdminState
        pending={query.isPending}
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      >
        {query.data ? (
          <>
            {!query.data.items.length ? (
              <p>No matching users.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[800px] text-left text-sm">
                  <thead>
                    <tr>
                      {[
                        "Name / Email",
                        "Role",
                        "Status",
                        "Buildings",
                        "Created (UTC)",
                        "Action",
                      ].map((label) => (
                        <th className="p-3" key={label}>
                          {label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {query.data.items.map((row) => (
                      <tr className="border-t" key={row.id} data-admin-user={row.id}>
                        <td className="p-3">
                          {row.full_name}
                          <p>{row.email}</p>
                        </td>
                        <td className="p-3">{row.role}</td>
                        <td className="p-3">{row.is_active ? "Active" : "Inactive"}</td>
                        <td className="p-3">{row.building_count}</td>
                        <td className="whitespace-nowrap p-3">
                          {row.created_at.replace("T", " ")}
                        </td>
                        <td className="p-3">
                          <Link
                            to="/admin/users"
                            search={{ user: String(row.id) }}
                            className="underline"
                          >
                            View account / status
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <AdminPagination
              total={query.data.total}
              offset={filters.offset ?? 0}
              onChange={(offset) => setFilters({ ...filters, offset })}
            />
          </>
        ) : null}
      </AdminState>
    </Panel>
  );
}
export function AdminUsers({ selected }: { selected: string | undefined }) {
  const id = adminSelectedId(selected);
  if (selected !== undefined && id === null)
    return (
      <Panel title="Invalid user selection">
        <Link to="/admin/users" search={{}} className="underline">
          Back to users
        </Link>
      </Panel>
    );
  return id === null ? <UsersList /> : <UserDetail key={id} id={id} />;
}
