#include "chat.h"
#include "chat-peg-parser.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
using json = common_json;
static std::string read(const char *p) { std::ifstream f(p, std::ios::binary); return {std::istreambuf_iterator<char>(f), {}}; }
int main(int argc, char **argv) { try {
 if (argc != 3) throw std::runtime_error("usage: template request");
 auto request = json::parse(read(argv[2]));
 if (request.contains("builder_fixture")) {
   auto fixture = request["builder_fixture"];
   auto parser = build_chat_peg_parser([&](common_chat_peg_builder &p) {
     return p.standard_json_tools(fixture.value("start", ""), fixture.value("end", ""),
       request["tools"], request.value("parallel_tool_calls", true), true, "name", "arguments",
       fixture.value("array_wrapped", false)) + p.end();
   });
   common_chat_parser_params pp;
   pp.format = COMMON_CHAT_FORMAT_PEG_NATIVE; pp.parser = parser;
   auto parsed = common_chat_parse(request["generated"].get<std::string>(), request.value("partial", false), pp);
   std::cout << json({{"parsed",parsed.to_json_oaicompat()}}).dump() << std::endl; return 0;
 }
 auto templates = common_chat_templates_init(nullptr, read(argv[1]), "<|begin_of_text|>", "<|im_end|>");
 common_chat_templates_inputs input;
 input.use_jinja = true; input.reasoning_format = COMMON_REASONING_FORMAT_NONE;
 for (auto &m : request["messages"]) {
   common_chat_msg msg; msg.role = m["role"].get<std::string>();
   if (m.contains("content") && m["content"].is_string()) msg.content = m["content"].get<std::string>();
   if (m.contains("tool_call_id")) msg.tool_call_id = m["tool_call_id"].get<std::string>();
   if (m.contains("tool_calls")) for (auto &c : m["tool_calls"]) msg.tool_calls.push_back({c["function"]["name"], c["function"]["arguments"], c["id"]});
   input.messages.push_back(msg);
 }
 if (request.contains("tools")) for (auto &t : request["tools"]) {
   auto f = t["function"]; input.tools.push_back({f["name"], f.value("description", ""), f["parameters"].dump()});
 }
 if (request.value("tool_choice", "auto") == "required") input.tool_choice = COMMON_CHAT_TOOL_CHOICE_REQUIRED;
 if (request.value("tool_choice", "auto") == "none") input.tool_choice = COMMON_CHAT_TOOL_CHOICE_NONE;
 input.parallel_tool_calls = request.value("parallel_tool_calls", true);
 if (request.contains("chat_template_kwargs")) for (auto i = request["chat_template_kwargs"].begin(); i != request["chat_template_kwargs"].end(); ++i) input.chat_template_kwargs[i.key()] = i.value().dump();
 auto applied = common_chat_templates_apply(templates.get(), input);
 json result = {{"template_source",common_chat_templates_source(templates.get())},{"prompt",applied.prompt},{"grammar",applied.grammar},{"generation_prompt",applied.generation_prompt},{"parser",applied.parser},{"format",common_chat_format_name(applied.format)}};
 if (request.contains("generated")) {
   common_chat_parser_params pp(applied); pp.parser.load(applied.parser);
   auto parsed = common_chat_parse(request["generated"].get<std::string>(), request.value("partial", false), pp);
   result["parsed"] = parsed.to_json_oaicompat();
 }
 std::cout << result.dump() << std::endl; return 0;
 } catch (const std::exception &e) { std::cerr << e.what() << std::endl; return 1; } }
