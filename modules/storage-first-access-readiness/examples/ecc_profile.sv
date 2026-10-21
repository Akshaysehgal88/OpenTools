package opentools_ecc39;
    typedef struct packed {
        logic [31:0] data;
        logic [38:0] corrected_codeword;
        logic [5:0] syndrome;
        logic overall_odd,correctable,uncorrectable;
    } decoded_t;

    function automatic logic [38:0] encode(input logic [31:0] data);
        logic [38:0] result;
        logic check;
        int bit_index;
        result='0;bit_index=0;
        for(int position=1;position<=38;position++)begin
            if((position & (position-1))!=0)begin result[position-1]=data[bit_index];bit_index++;end
        end
        for(int p=0;p<6;p++)begin
            check=0;
            for(int position=1;position<=38;position++)
                if((position & (1<<p))!=0)check^=result[position-1];
            result[(1<<p)-1]=check;
        end
        result[38]=^result[37:0];
        return result;
    endfunction

    function automatic decoded_t decode(input logic [38:0] word);
        decoded_t result;
        logic check;
        int bit_index;
        result='0;result.corrected_codeword=word;
        for(int p=0;p<6;p++)begin
            check=0;
            for(int position=1;position<=38;position++)
                if((position & (1<<p))!=0)check^=word[position-1];
            result.syndrome[p]=check;
        end
        result.overall_odd=^word;
        if(result.overall_odd)begin
            if(result.syndrome==0)begin result.correctable=1;result.corrected_codeword[38]^=1;end
            else if(result.syndrome<=38)begin result.correctable=1;result.corrected_codeword[result.syndrome-1]^=1;end
            else result.uncorrectable=1;
        end else if(result.syndrome!=0)result.uncorrectable=1;
        bit_index=0;
        for(int position=1;position<=38;position++)
            if((position & (position-1))!=0)begin result.data[bit_index]=result.corrected_codeword[position-1];bit_index++;end
        return result;
    endfunction

    function automatic logic [38:0] systematic(input logic [38:0] word);
        logic [38:0] result;
        int bit_index;
        result='0;bit_index=0;
        for(int position=1;position<=38;position++)
            if((position & (position-1))!=0)begin result[bit_index]=word[position-1];bit_index++;end
        for(int p=0;p<6;p++)result[32+p]=word[(1<<p)-1];
        result[38]=word[38];return result;
    endfunction
endpackage
