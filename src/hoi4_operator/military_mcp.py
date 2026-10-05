"""Typed semantic military tools. All GUI access remains opt-in."""

from typing import Any

import anyio
from mcp.types import ToolAnnotations

from .contracts import ActionResult


def register_military_tools(server, service):
    observation = ToolAnnotations(read_only_hint=False, destructive_hint=False,
                                  idempotent_hint=True, open_world_hint=False)
    mutation = ToolAnnotations(read_only_hint=False, destructive_hint=True,
                               idempotent_hint=True, open_world_hint=False)
    creation = ToolAnnotations(read_only_hint=False, destructive_hint=True,
                               idempotent_hint=False, open_world_hint=False)

    async def call(action, *arguments):
        runtime = service()
        if runtime is None:
            result = ActionResult(action)
            result.evidence["reason"] = "backend_unavailable"
            return result.as_dict()
        return await anyio.to_thread.run_sync(getattr(runtime, action), *arguments)

    @server.tool(annotations=observation, structured_output=True)
    async def get_armies() -> dict[str, Any]:
        """Observe limited first GER army and three known divisions. Both collections share a version; IDs expire on refresh. GUI data is incomplete."""
        return await call("get_armies")

    @server.tool(annotations=observation, structured_output=True)
    async def get_army(army_id: str) -> dict[str, Any]:
        """Revalidate a session-local army ID, then return a fresh land snapshot and the requested object."""
        return await call("get_army", army_id)

    @server.tool(annotations=observation, structured_output=True)
    async def get_divisions() -> dict[str, Any]:
        """Read 1. Infanterie, 1. Panzer and 10. Infanterie only; other divisions remain unobserved. Generates temporary IDs."""
        return await call("get_divisions")

    @server.tool(annotations=observation, structured_output=True)
    async def get_division(division_id: str) -> dict[str, Any]:
        """Revalidate a session-local division ID; game unit IDs, province and supply are UNKNOWN."""
        return await call("get_division", division_id)

    @server.tool(annotations=observation, structured_output=True)
    async def get_generals() -> dict[str, Any]:
        """Read a limited normal general picker. Character identity requires name and portrait; Manstein only."""
        return await call("get_generals")

    @server.tool(annotations=creation, structured_output=True)
    async def create_army(division_ids: list[str]) -> dict[str, Any]:
        """Normally create the first army from exactly one observed unassigned division. Single submission and repeated exact readback."""
        return await call("create_army", division_ids)

    @server.tool(annotations=mutation, structured_output=True)
    async def assign_divisions(army_id: str, division_ids: list[str]) -> dict[str, Any]:
        """Normally assign exactly one known unassigned division to the observed first army after assigning Manstein."""
        return await call("assign_divisions", army_id, division_ids)

    @server.tool(annotations=mutation, structured_output=True)
    async def remove_divisions_from_army(army_id: str, division_ids: list[str]) -> dict[str, Any]:
        """Normally remove 1. Panzer after verifying its confirmation dialog. Refuse removal of the last division; other removal dialogs are uncalibrated."""
        return await call("remove_divisions_from_army", army_id, division_ids)

    @server.tool(annotations=mutation, structured_output=True)
    async def assign_general(army_id: str, general_id: str) -> dict[str, Any]:
        """Normally assign GER_erich_von_manstein after checking full army membership, general portrait and name."""
        return await call("assign_general", army_id, general_id)

    @server.tool(annotations=observation, structured_output=True)
    async def get_fronts() -> dict[str, Any]:
        """Observe two fixed-camera GER/POL border markers and the first army's whole-plan switch. Incomplete order coverage; assigned divisions UNKNOWN."""
        return await call("get_fronts")

    @server.tool(annotations=creation, structured_output=True)
    async def create_frontline(army_id: str, target_id: str) -> dict[str, Any]:
        """Create a normal full border frontline at GER_POL_mainland or GER_POL_east_prussia. Requires the known three-member Manstein army and fixed verified camera."""
        return await call("create_frontline",army_id,target_id)

    @server.tool(annotations=mutation, structured_output=True)
    async def execute_plan(army_id: str) -> dict[str, Any]:
        """Activate the observed first army's whole-plan switch. Verifies its enabled Stop button; does not claim combat or offensive-line execution."""
        return await call("execute_plan",army_id)

    @server.tool(annotations=mutation, structured_output=True)
    async def stop_plan(army_id: str) -> dict[str, Any]:
        """Stop the observed first army's whole plan; repeated switch and known-border readback."""
        return await call("stop_plan",army_id)

    @server.tool(annotations=creation, structured_output=True)
    async def create_offensive_line(army_id: str, target: str) -> dict[str, Any]:
        """Create one offensive order on an observed existing mainland frontline toward GER_POL_mainland_Poznan_east or GER_POL_mainland_Poland_north_east. Requires an empty calibrated order viewport and repeated exact GUI confirmation; never retries submission."""
        return await call("create_offensive_line",army_id,target)

    @server.tool(annotations=mutation, structured_output=True)
    async def move_divisions(division_ids: list[str], province_id: int) -> dict[str, Any]:
        """Currently rejects: province identity and normal movement-order readback are uncalibrated."""
        return await call("move_divisions",division_ids,province_id)

    @server.tool(annotations=observation, structured_output=True)
    async def get_supply_status(army_id: str | None = None, front_id: str | None = None) -> dict[str, Any]:
        """Read known 1. Infanterie tooltip's 100% supply and 150% stockpile only. Army/front totals are UNKNOWN; front queries are uncalibrated."""
        return await call("get_supply_status", army_id, front_id)

    @server.tool(annotations=observation, structured_output=True)
    async def get_air_state() -> dict[str, Any]:
        """Observe one known fighter wing, its Brandenburg base, 80/100 aircraft, region and mission; other wings and efficiency remain UNKNOWN."""
        return await call("get_air_state")

    @server.tool(annotations=observation, structured_output=True)
    async def get_navy_state() -> dict[str, Any]:
        """Observe one 12-ship High Seas task force under the German navy, its home port and docked state. Missions, region IDs and other task forces UNKNOWN."""
        return await call("get_navy_state")

    @server.tool(annotations=observation, structured_output=True)
    async def get_air_wings() -> dict[str, Any]:
        """Observe 第132战斗机联队 only. Returns a session-local wing ID expiring on refresh, with exact name, type, base, count, region and missions."""
        return await call("get_air_wings")

    @server.tool(annotations=observation, structured_output=True)
    async def get_air_regions() -> dict[str, Any]:
        """Observe Eastern Germany strategic region 8 by normal GUI title and fixed camera. Air superiority and efficiency are UNKNOWN."""
        return await call("get_air_regions")

    @server.tool(annotations=mutation, structured_output=True)
    async def assign_air_wing(wing_id: str, region_id: int) -> dict[str, Any]:
        """Normally assign the observed 第132战斗机联队 to region 8 after verifying its visible title. Single submission with repeated exact readback."""
        return await call("assign_air_wing",wing_id,region_id)

    @server.tool(annotations=mutation, structured_output=True)
    async def set_air_mission(wing_id: str, mission: str) -> dict[str, Any]:
        """Set air_superiority or none for the known wing in region 8; refuse other active missions or unknown identity. Does not claim combat effectiveness."""
        return await call("set_air_mission",wing_id,mission)

    @server.tool(annotations=observation, structured_output=True)
    async def get_fleets() -> dict[str, Any]:
        """Observe 公海舰队 as object_type task_force, with parent fleet and all twelve ship names. Returns a temporary fleet_id; incomplete coverage."""
        return await call("get_fleets")

    @server.tool(annotations=mutation, structured_output=True)
    async def assign_fleet_region(fleet_id: str, region_id: int) -> dict[str, Any]:
        """Currently rejects: sea-region identity and task-force assignment readback are uncalibrated."""
        return await call("assign_fleet_region",fleet_id,region_id)

    @server.tool(annotations=mutation, structured_output=True)
    async def set_naval_mission(fleet_id: str, mission: str) -> dict[str, Any]:
        """Currently rejects: normal naval mission selection and readback are uncalibrated."""
        return await call("set_naval_mission",fleet_id,mission)
