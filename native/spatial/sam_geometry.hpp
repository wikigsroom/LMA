#pragma once
#include "image.hpp"
#include "depth.hpp"
#include "flexicubes.hpp"
#include <set>
namespace lma_spatial {
// Float tensor bicubic AA, a=-0.5, clipped and renormalized at boundaries.
// Kept separate from the OpenCV a=-0.75 and Pillow integer image paths.
inline Floats sam_resize(const Floats& input,int iw,int ih,int ow,int oh,int channels,bool nearest=false){
 require(iw>=1&&ih>=1&&iw<=4096&&ih<=4096&&ow>=1&&oh>=1&&ow<=2048&&oh<=2048&&channels>=1&&channels<=4&&input.size()==size_t(iw)*ih*channels,"Invalid SAM resize");
 if(nearest)return resize(input,iw,ih,ow,oh,channels,"nearest",false);
 auto cubic=[](double x){x=std::abs(x);return x<1?((1.5*x-2.5)*x)*x+1:x<2?((-.5*x+2.5)*x-4)*x+2:0;};
 struct Kernel{int start;std::vector<float> weights;};
 auto kernels=[&](int from,int to){std::vector<Kernel> all(to);double ratio=double(from)/to,filter=std::max(1.,ratio);
  for(int x=0;x<to;x++){double center=(x+.5)*ratio;int lo=std::max(0,int(center-2*filter+.5)),hi=std::min(from,int(center+2*filter+.5));auto& k=all[x];k.start=lo;double sum=0;for(int j=lo;j<hi;j++){double v=cubic((j+.5-center)/filter);k.weights.push_back(float(v));sum+=v;}require(std::abs(sum)>1e-10,"Empty SAM resize filter");for(float& v:k.weights)v=float(v/sum);}return all;};
 auto xs=kernels(iw,ow),ys=kernels(ih,oh);Floats tmp(size_t(ow)*ih*channels),out(size_t(ow)*oh*channels);
 for(int y=0;y<ih;y++)for(int x=0;x<ow;x++)for(int c=0;c<channels;c++){float sum=0;auto& k=xs[x];for(size_t j=0;j<k.weights.size();j++)sum+=input[(size_t(y)*iw+k.start+j)*channels+c]*k.weights[j];tmp[(size_t(y)*ow+x)*channels+c]=sum;}
 for(int y=0;y<oh;y++)for(int x=0;x<ow;x++)for(int c=0;c<channels;c++){float sum=0;auto& k=ys[y];for(size_t j=0;j<k.weights.size();j++)sum+=tmp[(size_t(k.start+j)*ow+x)*channels+c]*k.weights[j];out[(size_t(y)*ow+x)*channels+c]=sum;}return out;
}
inline Floats sam_chw(const Floats& hwc,int channels){require(channels>=1&&channels<=4&&hwc.size()%channels==0,"Invalid SAM channel layout");size_t pixels=hwc.size()/channels;Floats out(hwc.size());for(size_t i=0;i<pixels;i++)for(int c=0;c<channels;c++)out[c*pixels+i]=hwc[i*channels+c];return out;}
struct SamImage {int w=0,h=0;Floats rgb,mask,points,valid;};
inline SamImage sam_image(const fs::path& path){
 int w,h,c;require(fs::is_regular_file(path)&&!fs::is_symlink(path)&&fs::file_size(path)<=16*1024*1024&&stbi_info(path.string().c_str(),&w,&h,&c)&&w>=2&&h>=2&&uint64_t(w)*h<=4194304,"Use a bounded local RGBA PNG");
 std::unique_ptr<stbi_uc,decltype(&stbi_image_free)> rgba(stbi_load(path.string().c_str(),&w,&h,&c,4),stbi_image_free);require(bool(rgba),"Cannot read SAM PNG");SamImage out;out.w=w;out.h=h;out.rgb.resize(size_t(w)*h*3);out.mask.resize(size_t(w)*h);bool foreground=false,transparent=false;
 for(size_t i=0;i<out.mask.size();i++){out.mask[i]=rgba.get()[i*4+3]/255.f;foreground|=out.mask[i]>.5f;transparent|=out.mask[i]<1;for(int k=0;k<3;k++)out.rgb[i*3+k]=rgba.get()[i*4+k]/255.f;}
 require(foreground&&transparent,"Select a nonempty RGBA mask or run the local segmentation recipe first");return out;
}
struct SamMoments {float scale=1;std::array<float,3> shift{};};
inline float sam_median(Floats v){require(!v.empty(),"SAM normalization has no valid points");size_t index=(v.size()-1)/2;std::nth_element(v.begin(),v.begin()+index,v.end());return v[index];}
inline SamMoments sam_normalize_points(SamImage& image,const json& settings){
 size_t n=size_t(image.w)*image.h;require(image.points.size()==n*3&&image.valid.size()==n&&image.mask.size()==n,"Unmatched SAM point map");SamMoments out;std::string method=settings.at("method");require(method=="ssi"||method=="object_scene"||method=="object_quantile"||method=="object_norm_median","Unsupported SAM point normalizer");
 std::array<Floats,3> object;Floats z;for(size_t i=0;i<n;i++)if(image.valid[i]>.5f){for(int a=0;a<3;a++)require(std::isfinite(image.points[i*3+a]),"Nonfinite valid SAM point");z.push_back(image.points[i*3+2]);if(image.mask[i]>.5f)for(int a=0;a<3;a++)object[a].push_back(image.points[i*3+a]);}
 require(!z.empty(),"Depth model produced no valid points");
 if(method=="ssi"){out.shift[2]=sam_median(z);double sum=0;for(size_t i=0;i<n;i++)if(image.valid[i]>.5f)for(int a=0;a<3;a++)sum+=std::abs(image.points[i*3+a]-out.shift[a]);out.scale=float(sum/(3*z.size()));}
 else {for(int a=0;a<3;a++)out.shift[a]=sam_median(object[a]);Floats scale;
  for(size_t i=0;i<n;i++)if(image.valid[i]>.5f&&(method=="object_scene"||image.mask[i]>.5f)){float mx=0,d=0;for(int a=0;a<3;a++){float x=image.points[i*3+a]-out.shift[a];mx=std::max(mx,std::abs(x));d+=x*x;}scale.push_back(method=="object_scene"?mx:std::sqrt(d));}
  if(method=="object_quantile"){float q=settings.value("quantile",.1f);require(q>=0&&q<.5f,"Invalid SAM normalization quantile");std::sort(scale.begin(),scale.end());auto quantile=[&](float x){double p=x*(scale.size()-1);size_t i=size_t(p);return scale[i]+float(p-i)*(scale[std::min(i+1,scale.size()-1)]-scale[i]);};out.scale=2*(quantile(1-q)-quantile(q));}else out.scale=sam_median(scale);
 }
 float factor=settings.value("scaleFactor",1.f),clip=settings.value("clip",0.f);require(std::isfinite(factor)&&factor>0&&factor<=100&&std::isfinite(clip)&&clip>=0&&clip<=1000,"Invalid SAM normalization bounds");out.scale*=factor;require(std::isfinite(out.scale)&&out.scale>1e-12f,"Degenerate SAM normalization scale");
 for(size_t i=0;i<n;i++){float norm=0;for(int a=0;a<3;a++){image.points[i*3+a]=image.valid[i]>.5f?(image.points[i*3+a]-out.shift[a])/out.scale:0;norm+=image.points[i*3+a]*image.points[i*3+a];}if(clip>0&&norm>clip*clip){image.valid[i]=0;for(int a=0;a<3;a++)image.points[i*3+a]=0;}}return out;
}
struct SamInputs {std::map<std::string,Floats> values;SamMoments moments;};
inline SamInputs sam_inputs(SamImage image,int size,const json& preprocessing,bool with_points){
 require(size>=14&&size<=1024&&image.rgb.size()==size_t(image.w)*image.h*3&&image.mask.size()==size_t(image.w)*image.h,"Invalid SAM conditioning image");SamInputs out;
 if(with_points)out.moments=sam_normalize_points(image,preprocessing.at("normalizer"));
 int x0=image.w,y0=image.h,x1=-1,y1=-1;for(int y=0;y<image.h;y++)for(int x=0;x<image.w;x++)if(image.mask[size_t(y)*image.w+x]>0){x0=std::min(x0,x);x1=std::max(x1,x);y0=std::min(y0,y);y1=std::max(y1,y);}
 require(x1-x0>=2&&y1-y0>=2,"SAM mask bounds must span at least 2 pixels on each axis");float box=preprocessing.at("boxFactor"),padding=preprocessing.at("padding");require(std::isfinite(box)&&box>=1&&box<=3&&std::isfinite(padding)&&padding>=0&&padding<=1,"Invalid SAM crop profile");
 int boxsize=int(std::max({x1-x0,y1-y0,2})*box),left=int((x0+x1)/2.-boxsize/2),top=int((y0+y1)/2.-boxsize/2),right=int((x0+x1)/2.+boxsize/2),bottom=int((y0+y1)/2.+boxsize/2),side=std::max(right-left,bottom-top),border=int(side*padding),crop_side=side+2*border;
 require(side>0&&crop_side<=16384,"SAM crop exceeds bounds");int crop_left=left,crop_top=top;left-=(side-(right-left))/2+border;top-=(side-(bottom-top))/2+border;
 auto region=[&](int sx,int sy,int n,bool cropped){require(uint64_t(n)*n*3<=64000000,"SAM preprocessing memory budget exceeded");Floats rgb(size_t(n)*n*3,0),mask(size_t(n)*n,0),points,valid;if(with_points){points.resize(rgb.size());valid.resize(mask.size());}
  for(int y=0;y<n;y++)for(int x=0;x<n;x++){int xx=x+sx,yy=y+sy;if(xx<0||yy<0||xx>=image.w||yy>=image.h||(cropped&&(xx<crop_left||xx>=right||yy<crop_top||yy>=bottom)))continue;size_t src=size_t(yy)*image.w+xx,dst=size_t(y)*n+x;mask[dst]=image.mask[src];for(int a=0;a<3;a++)rgb[dst*3+a]=image.rgb[src*3+a]*(cropped?image.mask[src]:1);if(with_points){valid[dst]=image.valid[src]*(cropped&&image.mask[src]<=0?0:1);for(int a=0;a<3;a++)points[dst*3+a]=valid[dst]>.5f?image.points[src*3+a]:0;}}
  out.values[cropped?"image":"rgb_image"]=sam_chw(sam_resize(rgb,n,n,size,size,3),3);out.values[cropped?"mask":"rgb_image_mask"]=sam_resize(mask,n,n,size,size,1,true);
  if(with_points){std::string key=cropped?"pointmap":"rgb_pointmap";out.values[key]=sam_chw(sam_resize(points,n,n,size,size,3,true),3);out.values[key+"_valid"]=sam_resize(valid,n,n,size,size,1,true);}
 };
 region(left,top,crop_side,true);int full=std::max(image.w,image.h);region(-(full-image.w)/2,-(full-image.h)/2,full,false);return out;
}
inline std::vector<lma_sparse::Coord> sam_occupancy(const Floats& occupancy,int grid,int prune,int maximum,int& factor,std::mt19937& random){
 require(grid>=4&&grid<=256&&occupancy.size()==size_t(grid)*grid*grid&&prune>=0&&prune<=2&&maximum>=1&&maximum<=42000,"Invalid SAM occupancy profile");lma_sparse::finite(occupancy);std::vector<lma_sparse::Coord> all;
 for(int x=0;x<grid;x++)for(int y=0;y<grid;y++)for(int z=0;z<grid;z++)if(occupancy[(size_t(x)*grid+y)*grid+z]>0){require(all.size()<lma_sparse::point_limit,"SAM occupancy support exceeds memory budget");all.push_back({0,x,y,z});}require(!all.empty(),"SAM occupancy contains no foreground");
 if(prune){std::set<lma_sparse::Coord> present(all.begin(),all.end());std::vector<lma_sparse::Coord> surface;int full=(2*prune+1)*(2*prune+1)*(2*prune+1);for(auto c:all){int count=0;for(int x=-prune;x<=prune;x++)for(int y=-prune;y<=prune;y++)for(int z=-prune;z<=prune;z++)count+=present.count({0,c[1]+x,c[2]+y,c[3]+z});if(count<full)surface.push_back(c);}all=std::move(surface);}
 factor=1;if(all.size()>42000){std::array<float,3> lo={float(grid),float(grid),float(grid)},hi={0,0,0};for(auto c:all)for(int a=0;a<3;a++){lo[a]=std::min(lo[a],float(c[a+1]));hi[a]=std::max(hi[a],float(c[a+1]));}
  std::set<lma_sparse::Coord> reduced;for(auto c:all){for(int a=0;a<3;a++){float range=hi[a]-lo[a];require(range>0,"Degenerate SAM structure bounds");float target=(range+1)/2,low=lo[a]+(range+1-target)/2,high=low+target-1;c[a+1]=std::clamp<int64_t>(int64_t(std::nearbyint((float(c[a+1])-lo[a])/range*(target-1)+low)),int64_t(low),int64_t(high));}reduced.insert(c);}all.assign(reduced.begin(),reduced.end());if(all.size()>42000){std::shuffle(all.begin(),all.end(),random);all.resize(42000);}factor=2;
 }
 require(!all.empty()&&all.size()<=size_t(maximum),"SAM sparse decoder exceeds selected row budget; no latent support was silently truncated");return all;
}
inline void sam_glb(const fs::path& path,const FlexMesh& surface,const json& extras){
 const auto& mesh=surface.mesh;size_t n=mesh.vertices.size();require(n>0&&!mesh.indices.empty()&&(surface.colors.empty()||surface.colors.size()==n),"Invalid SAM surface colors");
 json root={{"asset",{{"version","2.0"},{"generator","LMA SAM CPU"}}},{"scene",0},{"scenes",json::array({{{"nodes",{0}}}})},{"nodes",json::array({{{"mesh",0}}})},{"bufferViews",json::array()},{"accessors",json::array()},{"extras",extras}};
 std::vector<uint8_t> binary;auto attribute=[&](const void* p,size_t length,int component,size_t count,const char* type,int target){size_t offset=binary.size();const auto* b=static_cast<const uint8_t*>(p);binary.insert(binary.end(),b,b+length);int id=int(root["bufferViews"].size());root["bufferViews"].push_back({{"buffer",0},{"byteOffset",offset},{"byteLength",length},{"target",target}});root["accessors"].push_back({{"bufferView",id},{"componentType",component},{"count",count},{"type",type}});return id;};
 int pos=attribute(mesh.vertices.data(),n*sizeof(Point),5126,n,"VEC3",34962);Point low=mesh.vertices[0],high=low;for(auto v:mesh.vertices)for(int a=0;a<3;a++){require(std::isfinite(v[a]),"Nonfinite SAM surface");low[a]=std::min(low[a],v[a]);high[a]=std::max(high[a],v[a]);}root["accessors"][pos]["min"]=low;root["accessors"][pos]["max"]=high;
 std::vector<Point> normals(n);for(size_t i=0;i<mesh.indices.size();i+=3){auto a=mesh.indices[i],b=mesh.indices[i+1],c=mesh.indices[i+2];require(a<n&&b<n&&c<n,"Invalid SAM face index");auto normal=cross(subtract(mesh.vertices[b],mesh.vertices[a]),subtract(mesh.vertices[c],mesh.vertices[a]));for(auto index:{a,b,c})for(int k=0;k<3;k++)normals[index][k]+=normal[k];}for(auto& v:normals){float norm=std::sqrt(dot(v,v));if(norm>1e-12f)for(float& x:v)x/=norm;}
 json attrs={{"POSITION",pos},{"NORMAL",attribute(normals.data(),n*sizeof(Point),5126,n,"VEC3",34962)}};
 if(!surface.colors.empty()){std::vector<Point> color(n),aux(n);for(size_t i=0;i<n;i++)for(int a=0;a<3;a++){require(std::isfinite(surface.colors[i][a])&&std::isfinite(surface.colors[i][a+3]),"Nonfinite SAM attributes");color[i][a]=surface.colors[i][a];aux[i][a]=surface.colors[i][a+3];}attrs["COLOR_0"]=attribute(color.data(),n*sizeof(Point),5126,n,"VEC3",34962);attrs["_SAM_AUX"]=attribute(aux.data(),n*sizeof(Point),5126,n,"VEC3",34962);}
 int indices=attribute(mesh.indices.data(),mesh.indices.size()*4,5125,mesh.indices.size(),"SCALAR",34963);root["materials"]=json::array({{{"pbrMetallicRoughness",{{"baseColorFactor",{1,1,1,1}},{"metallicFactor",0},{"roughnessFactor",1}}},{"doubleSided",true}}});root["meshes"]=json::array({{{"primitives",json::array({{{"attributes",attrs},{"indices",indices},{"material",0},{"mode",4}}})}}});root["buffers"]=json::array({{{"byteLength",binary.size()}}});
 std::string metadata=root.dump();while(metadata.size()%4)metadata+=' ';while(binary.size()%4)binary.push_back(0);require(metadata.size()<8*1024*1024&&metadata.size()+binary.size()+28<=512*1024*1024,"SAM GLB exceeds output budget");std::unique_ptr<FILE,decltype(&std::fclose)> file(std::fopen(path.string().c_str(),"wb"),std::fclose);require(bool(file),"Cannot create SAM GLB");u32(file.get(),0x46546c67);u32(file.get(),2);u32(file.get(),uint32_t(28+metadata.size()+binary.size()));u32(file.get(),uint32_t(metadata.size()));u32(file.get(),0x4e4f534a);std::fwrite(metadata.data(),1,metadata.size(),file.get());u32(file.get(),uint32_t(binary.size()));u32(file.get(),0x004e4942);std::fwrite(binary.data(),1,binary.size(),file.get());require(!std::ferror(file.get())&&!std::fflush(file.get())&&!LMA_SYNC(LMA_FILENO(file.get())),"Cannot persist SAM surface");
}
}
