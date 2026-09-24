import Keycloak from 'keycloak-js'

/**
 * Keycloak instance configured to communicate exclusively through Kong Gateway.
 *
 * All OIDC discovery, authorization redirects, and token exchange requests
 * hit Kong (http://localhost:8000/auth), which proxies them securely to Keycloak.
 */
const gatewayUrl = (import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8000').replace(/\/+$/, '')
const keycloakUrl = import.meta.env.VITE_KEYCLOAK_URL || `${gatewayUrl}/auth`

const keycloakConfig = {
  url: keycloakUrl,
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'mentor',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'mentor-frontend',
}

const keycloak = new Keycloak(keycloakConfig)

let initPromise = null

/**
 * Singleton initializer that guards against React 18/19 StrictMode double-mounting.
 * Ensures keycloak.init() is only ever called once across the entire application lifecycle.
 */
export function initKeycloak() {
  if (!initPromise) {
    initPromise = keycloak
      .init({
        onLoad: 'login-required',
        checkLoginIframe: false,
        pkceMethod: 'S256',
      })
      .catch((err) => {
        initPromise = null // Allow retry on transient failure
        throw err
      })
  }
  return initPromise
}

export default keycloak
