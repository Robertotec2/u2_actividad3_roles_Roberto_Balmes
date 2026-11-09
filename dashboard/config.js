// Direccion del API GraphQL.
// - Servido por FastAPI en http://localhost:8000/dashboard/ -> "/graphql" (mismo origen, sin CORS)
// - Servido aparte (por ejemplo en http://localhost:5173) -> "http://localhost:8000/graphql"
//   y en el backend CORS_ORIGINS=http://localhost:5173
window.DASHBOARD_CONFIG = {
  graphqlUrl: "/graphql",
};
