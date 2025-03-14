'''
Author: lihaitao
Date: 2023-05-20 15:06:50
LastEditors: Do not edit
LastEditTime: 2023-05-20 19:32:43
'''
from transformers import AutoModel
import torch
import os
os.environ["CUDA_VISIBLE_DEVICES"] = '7'
import sys
sys.path.append("../src") 
from modeling_chatglm import ChatGLMForConditionalGeneration
from tokenization_chatglm import ChatGLMTokenizer
from tqdm import tqdm
from peft import PeftModel
import argparse, json

def generate(model, tokenizer, text):
    with torch.no_grad():
        input_text = text
        ids = tokenizer.encode(input_text)
        input_ids = torch.LongTensor([ids]).cuda()
        output = model.generate(
            input_ids=input_ids,
            max_new_tokens=2048,
            do_sample=False,
            temperature=0.7,
            num_return_sequences=1
        )[0]
        output = tokenizer.decode(output)
        answer = output[len(input_text):]
    return answer.strip()
    
def process_dataset(model, tokenizer, dataset_path, output_path):
    # Load the dataset
    test_result = []
    with open(dataset_path, "r") as f:
        for line in tqdm(f):
            one = json.loads(line.strip())
            prompt = f"""
{one['input']}
请根据上面提供的事实描述，生成一篇完整且具有法律效力的中文的刑事判决书。生成的文书必须结构严谨、逻辑清晰，并且要包含以下个部分：

1. 开头
2. **事实描述**  
\- 请直接复述以下提供的事实描述，不得进行删减或改动：

3. **司法理由**  
\- 根据上述事实描述，结合相关刑法条款、法律原则和司法解释，详细论述案件的法律分析，以“本院认为”开头。  
\- 分析内容应包括：  
​     \- 对证据的评估  
​     \- 犯罪构成要件的论证  
​     \- 相关法律条文的引用及其适用说明  
   \- 请确保推理过程严谨、论证充分，为判决结果提供充分法律依据。

4. **判决结果**  
\- 在此部分明确给出法院的最终判决，以“判决如下”开头。  
\- 判决内容应具体包括处罚措施（如刑期、罚金、附加刑等）及其法律依据，确保与前述司法理由相呼应，文书整体逻辑连贯。

**注意：**  确保文书所有部分均符合真实司法文书的写作规范，语言应正式、客观、清晰。
"""
            gen_ans = generate(model, tokenizer, prompt)
            exp_ans = one['output']
            print(f"Generated answer: {gen_ans}")

            # Update data and add to results list
            entry = {
                "gen_ans": gen_ans,
                "exp_ans": exp_ans
            }
            test_result.append(entry)

    # Save the results
    with open(output_path, 'w') as f:
        json.dump(test_result, f, ensure_ascii=False, indent=4)
    print(f"Results saved to {output_path}")
    
    
if __name__ == "__main__":
    model_name = "../model/LexiLaw"
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--base_model", type=str, default="../model/LexiLaw")
    argparser.add_argument("--adapter", type=str, default="../model/full")
    argparser.add_argument("--interactive", default=True)
    args = argparser.parse_args()

    model = ChatGLMForConditionalGeneration.from_pretrained(args.base_model, trust_remote_code=True)
    tokenizer = ChatGLMTokenizer.from_pretrained(model_name, trust_remote_code=True)
    peft_model = PeftModel.from_pretrained(model, args.adapter).eval()
    
    peft_model.half().cuda()
    torch.set_default_tensor_type(torch.cuda.FloatTensor)

    
    dataset_path = "/liuzyai04/thuir/yuebaoqing/casegen/data/test.json"
    output_path = "/liuzyai04/thuir/yuebaoqing/casegen/output/lexilaw.json"
    process_dataset(peft_model, tokenizer, dataset_path, output_path)

