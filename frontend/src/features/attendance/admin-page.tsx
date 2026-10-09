import { useAttendanceWorkspace } from "./hooks";
import { Heading } from "./ui";
export function AdminPage() {
  const { data } = useAttendanceWorkspace();
  if (!data) return null;
  return <><Heading title={<>Admin <em>View</em></>} description="An overview of this attendance workspace." />
    <div className="stats">{[["Workshops", data.workshops.length], ["Active students", data.students.filter((s) => !s.archived).length], ["Archived students", data.students.filter((s) => s.archived).length], ["Mail drafts", data.drafts.length]].map(([label, value]) => <div className="stat" key={label}><b>{value}</b><span>{label}</span></div>)}</div>
    <div className="panel"><h2>Workspace details</h2><div className="table-wrap"><table><tbody><tr><th>Organizer</th><td>Rakesh Bhugra</td></tr><tr><th>Mode</th><td>Demo with temporary sample data</td></tr><tr><th>Student roster</th><td>Shared across workshops</td></tr><tr><th>Permissions</th><td>Organizer accounts and access controls are future additions.</td></tr></tbody></table></div></div>
  </>;
}
