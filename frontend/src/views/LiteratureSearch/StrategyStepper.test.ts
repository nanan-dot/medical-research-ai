import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import StrategyStepper from "./StrategyStepper.vue";

describe("StrategyStepper", () => {
  it("uses semantic step navigation and emits the selected section", async () => {
    const wrapper = mount(StrategyStepper, { props: { activeStep: 2 } });
    expect(wrapper.get('[aria-current="step"]').text()).toContain("检索意图");
    await wrapper.findAll("button")[2].trigger("click");
    expect(wrapper.emitted("select")).toEqual([[3]]);
  });
});
