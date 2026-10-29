#include "moss_tts.h"
#include "audio_tokenizer.hpp"
#include "model_loader.hpp"
#include "backend.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>

// Existing pinned, untrained stereo fixture. Tests the real wrapper, partial codebooks,
// stateful graphs and sliding-window eviction; it is not a Realtime speech checkpoint.
int main(int argc,char** argv){if(argc!=2)return 2;int passed=0;double worst=0;moss::ModelLoader metadata;if(!metadata.load(argv[1]))return 3;
    int frames=int(metadata.get_u32("ref.n_frames",0)),depth=int(metadata.get_u32("ref.rvq",0)),down=int(metadata.get_u32("moss.at.downsample",0));std::vector<int32_t> codes;moss::read_tensor_i32(metadata.tensor("ref.codes"),&codes);
    if(frames<8 || depth<2 || down<1)return 4;
    moss::Codec codec;if(!codec.load(argv[1]))return 5;
    for(int width:{depth,depth/2}){std::vector<int32_t> selected;for(int f=0;f<frames;f++)for(int i=0;i<width;i++)selected.push_back(codes[f*depth+i]);std::vector<float> full;if(!codec.decode(selected,frames,&full,width))return 6;
        auto state=codec.stream_begin();if(!state)return 7;std::vector<float> accumulated;
        for(int f=0;f<frames;f++){std::vector<int32_t> frame(selected.begin()+f*width,selected.begin()+(f+1)*width);std::vector<float> block;if(!codec.stream_step(*state,frame,&block) || int(block.size())!=down*2)return 8;accumulated.insert(accumulated.end(),block.begin(),block.end());passed++;}
        if(full.size()!=accumulated.size())return 9;for(size_t i=0;i<full.size();i++){double error=std::fabs(double(full[i])-accumulated[i]);if(!std::isfinite(error)||error>1e-3)return 10;worst=std::max(worst,error);}passed++;
        std::vector<float> ignored;if(codec.stream_step(*state,{},&ignored)||codec.stream_step(*state,std::vector<int32_t>(width+1,0),&ignored))return 11;passed++;
    }
    std::cout<<"{\"passed\":"<<passed<<",\"stream_vs_batch_max_abs_error\":"<<worst<<",\"fixture_frames\":"<<frames<<",\"partial_codebook_depth\":"<<depth/2<<",\"sliding_window_crossed\":true,\"model_inference\":false}"<<std::endl;
}
