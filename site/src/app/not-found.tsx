import Link from "next/link";

export default function NotFound() {
  return (
    <div className="wrap page">
      <p className="crumb">404</p>
      <h1 style={{ marginTop: 14 }}>That page is not here.</h1>
      <p className="sub">
        If you followed a link to a role, it closed more than 45 days ago and has been cleared. The current list is one click away.
      </p>
      <div className="actions">
        <Link className="btn" href="/">
          See open roles
        </Link>
      </div>
    </div>
  );
}
