import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import DynamicForm from "../../components/DynamicForm.vue";
import type { FormField, FormSchemaDefinition } from "../../api/client";

function makeSchema(fields: FormField[]): FormSchemaDefinition {
  return { version: 1, fields };
}

function field(overrides: Partial<FormField> & { key: string; label: string; type: FormField["type"] }): FormField {
  return { required: false, ...overrides };
}

describe("DynamicForm", () => {
  it("text type → 渲染 <input type='text'>", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([field({ key: "name", label: "Name", type: "text" })]),
        modelValue: { name: "" },
      },
    });
    expect(wrapper.find("input[type='text']").exists()).toBe(true);
  });

  it("email type → 渲染 <input type='email'>", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([field({ key: "email", label: "Email", type: "email" })]),
        modelValue: { email: "" },
      },
    });
    expect(wrapper.find("input[type='email']").exists()).toBe(true);
  });

  it("number type → 渲染 <input type='number'>", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([field({ key: "age", label: "Age", type: "number" })]),
        modelValue: { age: "" },
      },
    });
    expect(wrapper.find("input[type='number']").exists()).toBe(true);
  });

  it("single_select → 渲染 <select> + 正確 option 數量", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([
          field({ key: "style", label: "Style", type: "single_select", options: ["Hiphop", "Popping", "Locking"] }),
        ]),
        modelValue: { style: "" },
      },
    });
    expect(wrapper.find("select").exists()).toBe(true);
    // 3 options + 1 placeholder "Select"
    expect(wrapper.findAll("option")).toHaveLength(4);
  });

  it("multi_select → 渲染對應數量的 checkbox", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([
          field({ key: "styles", label: "Styles", type: "multi_select", options: ["Hiphop", "Popping"] }),
        ]),
        modelValue: { styles: [] },
      },
    });
    expect(wrapper.findAll("input[type='checkbox']")).toHaveLength(2);
  });

  it("checkbox type → 渲染單一 checkbox", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([field({ key: "agree", label: "Agree", type: "checkbox" })]),
        modelValue: { agree: false },
      },
    });
    expect(wrapper.find("input[type='checkbox']").exists()).toBe(true);
  });

  it("required 欄位 → DOM 中有 * 標記", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([field({ key: "name", label: "Name", type: "text", required: true })]),
        modelValue: { name: "" },
      },
    });
    expect(wrapper.text()).toContain("*");
  });

  it("help_text 有值 → 渲染說明文字", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([
          field({ key: "name", label: "Name", type: "text", help_text: "請填寫真實姓名" }),
        ]),
        modelValue: { name: "" },
      },
    });
    expect(wrapper.text()).toContain("請填寫真實姓名");
  });

  it("text input 觸發 input 事件 → emit update:modelValue 含正確 key/value", async () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([field({ key: "name", label: "Name", type: "text" })]),
        modelValue: { name: "" },
      },
    });
    await wrapper.find("input").setValue("Andrew");
    const emitted = wrapper.emitted("update:modelValue");
    expect(emitted).toBeTruthy();
    expect(emitted![0][0]).toEqual({ name: "Andrew" });
  });

  it("select 觸發 change 事件 → emit update:modelValue 含正確 value", async () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([
          field({ key: "style", label: "Style", type: "single_select", options: ["Hiphop", "Popping"] }),
        ]),
        modelValue: { style: "" },
      },
    });
    await wrapper.find("select").setValue("Hiphop");
    const emitted = wrapper.emitted("update:modelValue");
    expect(emitted).toBeTruthy();
    expect(emitted![0][0]).toEqual({ style: "Hiphop" });
  });

  it("multi_select 勾選新項目 → emit 陣列中包含該選項", async () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([
          field({ key: "styles", label: "Styles", type: "multi_select", options: ["Hiphop", "Popping"] }),
        ]),
        modelValue: { styles: [] },
      },
    });
    await wrapper.findAll("input[type='checkbox']")[0].trigger("change");
    const emitted = wrapper.emitted("update:modelValue");
    expect(emitted).toBeTruthy();
    expect((emitted![0][0] as Record<string, unknown>)["styles"]).toContain("Hiphop");
  });

  it("disabled=true → 所有 input 有 disabled 屬性", () => {
    const wrapper = mount(DynamicForm, {
      props: {
        schema: makeSchema([
          field({ key: "name", label: "Name", type: "text" }),
          field({ key: "age", label: "Age", type: "number" }),
        ]),
        modelValue: { name: "", age: "" },
        disabled: true,
      },
    });
    wrapper.findAll("input").forEach((input) => {
      expect(input.attributes("disabled")).toBeDefined();
    });
  });
});
