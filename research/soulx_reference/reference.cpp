// SPDX-License-Identifier: MIT
// CPU reference model orchestration, with the same private ORT session policy
// as the acoustic chain. The input is decoded PCM, not an arbitrary graph feed.
#include "reference.hpp"
#include "../soulx_ort/runtime.hpp"

namespace lma::soulx {
using namespace ort;
PreparedReference prepare_reference(const ReferenceModels& models,const Samples& pcm,int threads,
        OrtStats& stats,Cancel cancelled,Progress progress,Trace trace) {
    stats={};require(threads>=1 && threads<=32,"Invalid SoulX reference thread count");
    require(pcm.size()>=24000 && pcm.size()<=kMaxReference24k,"SoulX reference must be 1 to 15 seconds at 24kHz");
    finite(pcm);for(float sample:pcm)require(std::abs(sample)<=1,"SoulX reference PCM must be normalized");
    auto event=[&](const char* stage,int done,int total){stop(cancelled);if(progress)progress(stage,done,total);stop(cancelled);};
    event("reference_features",0,1);auto features=reference_features(pcm,cancelled);event("reference_features",1,1);
    if(trace){
        trace("s3_features",features.semantic.values,{1,128,static_cast<int64_t>(features.semantic.cols)});
        trace("speaker_features",features.speaker.values,{1,static_cast<int64_t>(features.speaker.rows),80});
        trace("flow_features",features.flow.values,{1,80,static_cast<int64_t>(features.flow.cols)});
    }
    initialize();stats.runtime_version=OrtGetApiBase()->GetVersionString();Ort::Env env(ORT_LOGGING_LEVEL_FATAL,"lma-soulx-reference");
    PreparedReference result;result.source_samples=pcm.size();result.semantic_frames=features.semantic.cols;
    result.speaker_frames=features.speaker.rows;result.raw_flow_frames=features.flow.cols;
    {
        event("s3_tokenizer",0,1);
        Graph graph(env,models.directory,"reference-s3.onnx",threads,stats,
            {{"feats",f32,{1,128,-1}},{"feats_length",i32,{1}}},{{"indices",i32,{1,-1}}});
        std::vector<int32_t> length{static_cast<int32_t>(features.semantic.cols)};
        std::vector<Ort::Value> feed;feed.push_back(floats(features.semantic.values,{1,128,static_cast<int64_t>(features.semantic.cols)}));
        feed.push_back(int32s(length,{1}));event("reference_s3_run",0,1);auto outputs=graph.run(feed,cancelled);
        require(outputs.size()==1 && outputs[0].IsTensor(),"Wrong SoulX reference token output");
        auto info=outputs[0].GetTensorTypeAndShapeInfo();auto shape=info.GetShape();
        size_t expected=(features.semantic.cols+3)/4;
        require(info.GetElementType()==i32 && shape==std::vector<int64_t>{1,static_cast<int64_t>(expected)} &&
                expected>0 && expected<=375 && info.GetElementCount()==expected,"Invalid S3 reference token layout/rate");
        auto codes=outputs[0].GetTensorMutableData<int32_t>();result.tokens.assign(codes,codes+expected);
        for(auto code:result.tokens)require(code>=0 && code<6561,"Invalid S3 reference semantic code");
        result.raw_tokens=result.tokens.size();event("s3_tokenizer",1,1);
    }
    features.semantic.values.clear();
    {
        event("speaker_encoder",0,1);
        Graph graph(env,models.directory,"reference-speaker.onnx",threads,stats,
            {{"input",f32,{1,-1,80}}},{{"output",f32,{1,192}}});
        std::vector<Ort::Value> feed;feed.push_back(floats(features.speaker.values,{1,static_cast<int64_t>(features.speaker.rows),80}));
        event("reference_speaker_run",0,1);auto outputs=graph.run(feed,cancelled);result.speaker=output(outputs[0],{1,192});event("speaker_encoder",1,1);
    }
    auto aligned=align_prompt(result.tokens.size(),features.flow.cols);result.tokens.resize(aligned.token_count);
    result.prompt_mel={80,aligned.mel_frames,Samples(80*aligned.mel_frames)};
    for(size_t channel=0;channel<80;++channel)
        std::copy_n(features.flow.values.begin()+channel*features.flow.cols,aligned.mel_frames,result.prompt_mel.values.begin()+channel*aligned.mel_frames);
    if(trace){trace("speaker",result.speaker,{1,192});trace("prompt_mel",result.prompt_mel.values,{1,80,static_cast<int64_t>(aligned.mel_frames)});}
    require(stats.session_loads==2 && stats.session_unloads==2 && stats.max_live_sessions==1,"SoulX reference session lifetime mismatch");
    event("reference_complete",1,1);return result;
}
}
