#!/usr/bin/env python3
"""Create one source overlay for the panel described by recovered FEX/timings."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
src = root / '.tools/sources/linux-6.12/drivers/gpu/drm/panel/panel-simple.c'
out = root / '.tools/overlays/panel-simple-g739.c'
s = src.read_text()
s = s.replace('#include <linux/module.h>', '#include <linux/module.h>\n#include <linux/pwm.h>')
s = s.replace('struct panel_simple {', 'struct panel_simple {\n\tstruct pwm_device *g739_vcom;')
hook = '''static int g739_vcom_set(struct panel_simple *p, bool enabled)
{
    struct pwm_state state;

    if (!p->g739_vcom)
        return 0;
    pwm_init_state(p->g739_vcom, &state);
    /* Stock disp_lcdc_init: PWM1 period 66666ns, duty=period*200/1000. */
    state.duty_cycle = state.period / 5;
    state.enabled = enabled;
    return pwm_apply_might_sleep(p->g739_vcom, &state);
}

'''
needle_disable = 'static int panel_simple_disable(struct drm_panel *panel)'
assert s.count(needle_disable) == 1
s = s.replace(needle_disable, hook + needle_disable)
for which, enabled in [('enable', 'true'), ('disable', 'false')]:
    needle_func = f'static int panel_simple_{which}(struct drm_panel *panel)\n{{\n\tstruct panel_simple *p = to_panel_simple(panel);'
    assert s.count(needle_func) == 1
    s = s.replace(needle_func, needle_func + f'\n\tint ret = g739_vcom_set(p, {enabled});\n\n\tif (ret)\n\t\treturn ret;')
probe = '\tpanel->supply = devm_regulator_get(dev, "power");'
assert s.count(probe) == 1
s = s.replace(probe, '''    if (of_device_is_compatible(dev->of_node, "eurocase,g739-panel")) {
        panel->g739_vcom = devm_pwm_get(dev, "vcom");
        if (IS_ERR(panel->g739_vcom))
            return dev_err_probe(dev, PTR_ERR(panel->g739_vcom), "VCOM PWM unavailable\\n");
    }

''' + probe)
needle = 'static const struct of_device_id platform_of_match[] = {'
assert s.count(needle) == 1
panel = '''/* Eurocase polaris-g739: recovered stock FEX and LCD open-flow. */
static const struct drm_display_mode eurocase_g739_mode = {
    .clock = 52000,
    .hdisplay = 1024, .hsync_start = 1186, .hsync_end = 1206, .htotal = 1344,
    .vdisplay = 600, .vsync_start = 610, .vsync_end = 613, .vtotal = 635,
    .flags = DRM_MODE_FLAG_NHSYNC | DRM_MODE_FLAG_NVSYNC,
};

static const struct panel_desc eurocase_g739_panel = {
    .modes = &eurocase_g739_mode, .num_modes = 1, .bpc = 6,
    .size = { .width = 155, .height = 86 },
    .delay = { .prepare = 10, .enable = 100, .disable = 10, .unprepare = 30 },
    .bus_format = MEDIA_BUS_FMT_RGB666_1X18,
    .bus_flags = DRM_BUS_FLAG_DE_HIGH | DRM_BUS_FLAG_PIXDATA_DRIVE_NEGEDGE,
    .connector_type = DRM_MODE_CONNECTOR_DPI,
};

'''
s = s.replace(needle, panel + needle + '\n\t{ .compatible = "eurocase,g739-panel", .data = &eurocase_g739_panel },')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(s)
print(out)
