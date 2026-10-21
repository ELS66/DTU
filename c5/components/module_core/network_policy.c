#include "network_policy.h"
module_net_action_t module_network_boot_action(module_sim_t sim, bool wifi_ready, bool detection_complete)
{
    if (wifi_ready) return MODULE_NET_WIFI;
    if (!detection_complete) return MODULE_NET_WAIT;
    if (sim == MODULE_SIM_ABSENT) return MODULE_NET_PROVISION;
    if (sim == MODULE_SIM_PRESENT) return MODULE_NET_TRY_LTE;
    return MODULE_NET_WAIT;
}
module_net_action_t module_network_boot_step(module_boot_gate_t *gate, module_sim_t sim,
                                           bool wifi_ready, bool detection_complete)
{
    if (gate->closed) return MODULE_NET_WAIT;
    module_net_action_t action = module_network_boot_action(sim, wifi_ready, detection_complete);
    if (wifi_ready || detection_complete) gate->closed = true;
    return action;
}
module_sim_t module_sim_confirm(module_sim_filter_t *filter, module_sim_t observation)
{
    if (observation != MODULE_SIM_ABSENT) {
        filter->absent_count = 0;
        return observation;
    }
    if (filter->absent_count < 2) ++filter->absent_count;
    return filter->absent_count >= 2 ? MODULE_SIM_ABSENT : MODULE_SIM_UNKNOWN;
}
module_link_t module_route_choose(const module_route_policy_t *p, uint64_t now, bool wifi, bool lte)
{
    if (wifi && (!lte || now >= p->wifi_retry_after_ms)) return MODULE_LINK_WIFI;
    if (lte) return MODULE_LINK_LTE;
    return MODULE_LINK_NONE;
}
void module_route_result(module_route_policy_t *p, module_link_t link, bool success, uint64_t now)
{
    if (success) {
        if (link == MODULE_LINK_LTE && p->last_success != MODULE_LINK_LTE && now >= p->wifi_retry_after_ms)
            p->wifi_retry_after_ms = now + 30000;
        p->last_success = link;
        if (link == MODULE_LINK_WIFI) p->wifi_retry_after_ms = 0;
    } else {
        if (link == MODULE_LINK_WIFI) p->wifi_retry_after_ms = now + 30000;
        if (p->last_success == link) p->last_success = MODULE_LINK_NONE;
    }
}
