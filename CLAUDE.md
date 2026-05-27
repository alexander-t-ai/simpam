# Project Goal
Create a simple stand-alone IPAM system that is 1:1, one-to-one, compatible with NetBox' REST API
The system should support the lifecycle of network prefixes and IP addresses.

# Overall functionality
The system is a simple REST API server compatible with NetBox REST API. It provides endpoints for
manipulating network prefixes and IP addresses. The caller of the API should be able to perform basic
CRUD operations, as provided by NetBox, as well operations related to allocating addresses and prefixes.
Both IPv4 and IPv6 addresses should be supported. Incoming operations should be logged to the console, so
that they become accessible for "docker logs".

## Examples of endpoints that should be supported. Check them against the NetBox API!

- GET /prefixes/?role={role}
- GET /prefixes/{prefix-id}/available-ips/
- GET /prefixes/?role={role}&family={amily}
- POST /prefixes/{prefix-id}/available-prefixes/
- POST /prefixes/{prefix-id}/available-ips/
- DELETE /prefixes/{prefix-id}
- POST /ip-addresses/
- DELETE /ip-addresses/{ip-address-id}
- PATCH /ip-addresses/{ip-address-id}
- GET /ip-addresses/?address={ip-address}&mask_length={prefixlen}
- GET /ip-addresses/ip_address-id


# Technologies
* Python
* Docker with docker-compose.yaml file
* Python with FastAPI
* SqlLite for persistence

# Project structure
Use uv for package mangement. Structure the code according to best practices for production and test code.

# Testing
Implement integration tests: the test should make actual API calls using the requests library.
A typical test shoudld start be clearing the SqlLite database, then perform operations using the API and check the results also using the API;

Example test
1. Clear the database
2. Create a prefix
3. Get its available IPs
4. Create an IP address in the prefix
5. Read the addresses in the prefix and verify that one has been allocated

# References
NetBox REST API documentation: https://netboxlabs.com/docs/netbox/integrations/rest-api/
Detailed Swagger Documentation for the endpoints: https://demo.netbox.dev/api/schema/swagger-ui/

# Coding Conventions
Use modern python! 
* Don't use Optional[] rather use the construct '| None'.
* Don't split method arguments across multiple lines unless you have to do it to keep the line width.